# 시나리오 테스트 코드 컨벤션

> **이 문서는 "고쳐 쓰는 참고 구현"이다.** 아래 **핵심 원칙**("사전 데이터는 API로 만든다"·데이터 격리·자기 데이터만 삭제·FK 역순·전역 상태 불변·flush 함수 등)은 스택과 무관하게 **보편**이다. 이후의 구체 코드는 **Node.js + Jest + supertest + Sequelize(MySQL)** 스택 예시이며, 자기 스택에 맞게 교체한다. 바꿀 항목은 맨 아래 `프로젝트 커스터마이징` 주석 참고.

이 참고 구현의 시나리오 테스트는 **실제 app + supertest + 실제 DB**로 여러 API를 순서대로 호출하며 비즈니스 플로우를 검증한다. 단위 테스트가 API 1개에 집중한다면, 시나리오 테스트는 **유저가 실제로 앱을 사용하는 흐름**을 재현한다.

## 핵심 원칙

- **시나리오 1개 = 유저 플로우 1개**: 하나의 describe가 하나의 비즈니스 플로우를 담당
- **스텝 간 상태 전달**: 이전 API 호출의 결과(ID, 토큰 등)가 다음 API 호출의 입력
- **Helper 함수로 API 래핑**: 반복되는 API 호출은 헬퍼 함수로 분리, 실패 시 throw
- **TEST_PREFIX + DELETE로 데이터 격리**: 단위 테스트와 동일하게 TRUNCATE 금지, 자기 데이터만 관리
- **날짜 조작으로 시간 여행**: 비즈니스 로직의 날짜 의존성을 withFakeDate로 재현
- **단위 테스트와 중복 금지**: 개별 필드 검증, 401 테스트 등은 단위 테스트에서 커버

## 파일 위치

```
test/scenarios/{도메인}/{시나리오명}.spec.js
```

예시:
- `test/scenarios/challenge/slimbody/slimbody_score_test.spec.js`
- `test/scenarios/fnq/fnq_category_test.spec.js`
- `test/scenarios/community/post_lifecycle.spec.js`

## 사전 데이터는 API로 만든다 (DB INSERT 금지)

**시나리오 테스트는 "실제 유저가 앱을 쓰는 흐름"을 재현하는 것이 목적이다.**
`INSERT INTO ...` 로 DB를 직접 조작하면 실제 비즈니스 로직(validation, 부수 효과,
훅, 트랜잭션)이 건너뛰어져, 실서비스에선 절대 만들어질 수 없는 상태를 테스트하게 된다.
그러면 시나리오 테스트의 존재 의의가 사라진다.

**원칙**: 리소스를 만드는 API가 존재하면 **반드시 그 API를 호출**해서 만든다.

```javascript
// ❌ 절대 하지 않는다 — habitCards 생성 API가 있는데 INSERT로 만듦
await models.sequelize.query(
  `INSERT INTO habitCards (name, description, ...) VALUES (...)`,
  { replacements: { ... } },
);

// ✅ 어드민 API 호출로 실제 서비스 플로우 재현
const habitCardId = await createHabitCardViaApi({
  adminToken,
  name: `${TEST_PREFIX}-habit`,
  corporationId: krCorpId,
});
```

**예외 (INSERT 허용)**: 해당 데이터를 만드는 API가 **아예 존재하지 않는** 경우만.
- 법인(corporations), 국가 같은 시스템 레벨 메타 데이터 (대부분 SELECT로 조회만 함)
- 테스트 전용 시드 데이터로, 실서비스 플로우로는 절대 생성되지 않는 특수 상태

이 외에 "API 호출이 번거로워서" "빠르니까" 같은 이유로 INSERT를 쓰는 것은 금지.
단위 테스트는 INSERT 방식을 허용하지만 시나리오 테스트는 허용하지 않는다.

## 병렬 실행 안전 (데이터 격리)

**단위 테스트와 동일한 규칙을 따른다.** 시나리오 테스트라고 TRUNCATE를 쓰지 않는다.

### 규칙 1: TRUNCATE 금지 — 자기 데이터만 DELETE

```javascript
// ❌ 절대 하지 않는다 — 다른 테스트가 사용 중인 데이터도 날아감
await models.sequelize.query('TRUNCATE TABLE users');

// ✅ 자기가 만든 데이터만 삭제
await models.sequelize.query('DELETE FROM challenges WHERE id IN (:ids)', {
  replacements: { ids: createdIds.challenges },
});
await models.sequelize.query('DELETE FROM users WHERE id IN (:ids)', {
  replacements: { ids: createdIds.users },
});
```

### 규칙 2: TEST_PREFIX로 유니크한 테스트 데이터 생성

```javascript
// 파일명 기반 접두사 — 다른 테스트와 절대 겹치지 않음
const TEST_PREFIX = 'scenario.challenge.join';

const user = await createTestUser({
  name: `${TEST_PREFIX}-유저A`,
  email: `${TEST_PREFIX}-a@test.com`,
  provider: 'atomy',
  snsId: `${TEST_PREFIX}-001`,
  corporationId: 1,
});
```

### 규칙 3: createdIds로 모든 생성 리소스 추적

시나리오 테스트는 여러 API를 호출하며 여러 테이블에 데이터를 생성한다.
**테이블별로 생성된 ID를 추적**하여 afterAll에서 일괄 정리한다.

```javascript
describe('시나리오: 챌린지 참여 플로우', () => {
  const TEST_PREFIX = 'scenario.challenge.join';
  const createdIds = {
    users: [],
    challenges: [],
    habitCards: [],
    habitPacks: [],
    userHabitCardCompletes: [],
    challengeUserMapping: [],
  };

  // ... beforeAll에서 데이터 생성 시 ID 추적

  afterAll(async () => {
    // FK 역순으로 삭제 (자식 → 부모)
    const deleteOrder = [
      ['userHabitCardCompletes', 'id'],
      ['challengeUserMapping', 'id'],
      ['habitCardHabitPackMapping', 'id'],  // 이 테이블은 복합키일 수 있음
      ['habitPacks', 'id'],
      ['habitCards', 'id'],
      ['challenges', 'id'],
      ['account_country', 'account_id'],
      ['account', 'account_id'],
      ['system_account', 'system_account_id'],
      ['users', 'id'],
    ];

    for (const [table, idColumn] of deleteOrder) {
      const ids = createdIds[table];
      if (ids && ids.length > 0) {
        // eslint-disable-next-line no-await-in-loop
        await models.sequelize.query(
          `DELETE FROM \`${table}\` WHERE \`${idColumn}\` IN (:ids)`,
          { replacements: { ids } },
        );
      }
    }

    await models.sequelize.close();
  });
});
```

### 규칙 4: Helper 함수에서도 ID 추적

API 래퍼 함수가 리소스를 생성하면, 생성된 ID를 반환하여 호출자가 createdIds에 추가할 수 있게 한다.

```javascript
async function createChallengeViaApi({ sysToken, ...params }) {
  const res = await request(app)
    .post('/api/admin/challenge/create')
    .set('Authorization', `Bearer ${sysToken}`)
    .field(/* ... */);

  if (res.status !== 200) {
    throw new Error(`챌린지 생성 실패: ${res.status} ${JSON.stringify(res.body)}`);
  }

  // DB에서 생성된 ID 조회
  const [rows] = await models.sequelize.query(
    `SELECT id FROM challenges WHERE id = (SELECT MAX(id) FROM challenges)`,
  );
  return { challengeId: rows[0].id }; // 호출자가 createdIds.challenges.push()
}

// 사용 시
const result = await createChallengeViaApi({ sysToken, ... });
createdIds.challenges.push(result.challengeId);
```

### 규칙 5: API로 생성된 연관 데이터도 추적

어드민 API 하나가 여러 테이블에 데이터를 생성하는 경우 (예: 챌린지 생성 → challenges + habitPacks + challengeTranslations), 연관 테이블의 ID도 조회해서 추적한다.

```javascript
const result = await createChallengeViaApi({ sysToken, ... });
createdIds.challenges.push(result.challengeId);

// 연관 데이터도 추적
const packs = await models.HabitPack.findAll({
  where: { challengeId: result.challengeId },
  raw: true,
});
createdIds.habitPacks.push(...packs.map(p => p.id));
```

### 규칙 6: `SET FOREIGN_KEY_CHECKS=0` 절대 금지

FK 체크를 끄고 부모 row(`habitCards`, `users`, `corporations` 등)를 삭제하면 자식 테이블(`habitCardsTranslations`, `corporationTranslations` 등)에 **orphan row 가 남는다**. 이후 병렬 실행 중 다른 테스트가 새 부모 row 를 만들 때 auto-increment 가 orphan 의 FK 값과 겹치면 `UNIQUE(parentId, language)` 제약으로 **엉뚱한 테스트가 터진다**. cleanup 은 반드시 FK 순서대로 자식 → 부모로 DELETE 한다.

```javascript
// ❌ 금지
await models.sequelize.query('SET FOREIGN_KEY_CHECKS=0');
await models.sequelize.query('TRUNCATE TABLE habitCards');

// ✅ deleteOrder 로 자식부터 순서대로
const deleteOrder = [
  ['habitCardsTranslations', 'id'],  // 자식
  ['habitCardImages', 'id'],
  ['habitCards', 'id'],               // 부모
];
```

### 규칙 7: Translation 생성 직전 방어적 `destroy`

과거 실행의 잔여나 FK_CHECKS=0 버그로 translation 테이블에 orphan 이 있을 수 있다. `(parentId, language)` UNIQUE 충돌을 피하려면 bulkCreate 직전에 해당 parentId 로 destroy 한 번 호출한다.

```javascript
habitCard = await models.HabitCard.create({ ... });
createdIds.habitCards.push(habitCard.id);

// 방어적 orphan cleanup
await models.HabitCardTranslation.destroy({ where: { habitCardId: habitCard.id } });

await models.HabitCardTranslation.bulkCreate([
  { habitCardId: habitCard.id, language: 'ko', name: ... },
  { habitCardId: habitCard.id, language: 'en', name: ... },
]);
```

### 규칙 8: 전역 DB 상태를 UPDATE 하지 않는다

`Corporation.update({isActive: false}, {where:{}})` 처럼 범위가 넓은 update 는 같은 시점 도는 다른 worker 의 API 전제를 깨뜨린다. 전역 조회 결과를 테스트 중에만 제한하려면 **코드 레벨 monkey-patch** 를 쓴다. worker 프로세스 격리라 다른 worker 에 영향이 없다.

```javascript
// ❌ DB 전역 상태 변경 — 다른 worker 테스트가 isActive=true seed 를 기대하는데 깨짐
await models.Corporation.update({ isActive: false }, { where: {} });

// ✅ 이 worker 안에서만 유효한 monkey-patch
let originalFindAll;
function installFindAllPatch() {
  originalFindAll = models.Corporation.findAll.bind(models.Corporation);
  models.Corporation.findAll = async (opts) => {
    if (opts?.where?.isActive === true) return activeCorps;
    return originalFindAll(opts);
  };
}
function uninstallFindAllPatch() {
  if (originalFindAll) {
    models.Corporation.findAll = originalFindAll;
    originalFindAll = null;
  }
}
```

### 규칙 9: 스케줄러/글로벌 job 테스트는 "전용 법인" 으로 격리

`run()` 같은 scheduler job 은 `Corporation.findAll({isActive:true})` 로 **모든 활성 법인의 유저**를 순회한다. 다른 테스트가 seed KR 법인(id=1) 에 user 를 만들면 그 user 까지 타깃팅되어 `affectedUsers` 수치가 틀어진다. **beforeAll 에서 테스트 전용 Corporation 3개(KR/JP/NY)를 만들고** `Corporation.findAll` 을 monkey-patch 해서 그 전용 법인만 노출시킨다. 그 법인의 user 는 내 테스트가 만든 것뿐이므로 완전 격리된다.

```javascript
let testKrCorp, testJpCorp, testNyCorp;
let activeCorps = [];

beforeAll(async () => {
  const stamp = Date.now();
  testKrCorp = await models.Corporation.create({
    name: `__jobTest_KR_${stamp}`, timezoneName: 'Asia/Seoul', utcOffset: 540, isActive: false,
  });
  // ... testJpCorp, testNyCorp 동일 패턴
  installFindAllPatch();
});

afterAll(async () => {
  uninstallFindAllPatch();
  await cleanTables(); // 생성한 user/habit/... 정리
  await models.Corporation.destroy({ where: { id: [testKrCorp.id, testJpCorp.id, testNyCorp.id] } });
});
```

### 규칙 10: `count()` / `findAll()` 조건 없이 호출 금지

공유 테이블(`pushes`, `externalApiLogs` 등)에 조건 없이 `count()` 하면 다른 테스트 row 까지 섞인다. 내 테스트 job 의 특징 값으로 필터 건 count 만 assertion 에 쓴다.

```javascript
// ❌ 병렬 실행 중 다른 테스트가 만든 push 까지 카운트
expect(await models.Push.count()).toBe(2);

// ✅ 필터 조건 붙이기
expect(await models.Push.count({ where: { alarmType: ZERO_PUSH_ALARM_TYPE } })).toBe(2);
```

### 규칙 11: Push.userId 같이 하드코딩된 시스템 row 는 `INSERT IGNORE`

프로덕션 코드가 `Push.create({ userId: 1, ... })` 처럼 특정 id 를 하드코딩하는 경우가 있다 (시스템 유저). 이 row 는 여러 테스트가 공유하므로 create 시 `INSERT IGNORE` 로 "있으면 건드리지 말고" 처리하고, cleanup 에서도 삭제하지 않는다.

```javascript
async function seedSystemUser() {
  await models.sequelize.query(
    "INSERT IGNORE INTO users (id, createdAt, updatedAt, name, isGuest) VALUES (1, NOW(), NOW(), 'System', 0)",
  );
}
// cleanup 에서 id=1 은 스킵
```

## 시나리오 타입별 패턴

### 타입 A: 라이프사이클/CRUD

리소스의 전체 생명주기를 검증. 생성 → 조회 → 수정 → 삭제 + 권한/검색/필터.

```javascript
const TEST_PREFIX = 'scenario.fnq.category';

describe('FNQ 카테고리 관리 시나리오', () => {
  let sysToken;
  const createdIds = { system_account: [], categories: [], fnqs: [] };

  beforeAll(async () => {
    const sysAccount = await createTestSystemAccount({
      system_account_uuid: `${TEST_PREFIX}-sys`,
      email: `${TEST_PREFIX}-sys@test.com`,
    });
    sysToken = generateSystemAdminToken(sysAccount.system_account_id);
    createdIds.system_account.push(sysAccount.system_account_id);
  });

  afterAll(async () => {
    // FK 역순으로 자기 데이터만 삭제
    if (createdIds.fnqs.length > 0) {
      await models.sequelize.query('DELETE FROM fnqs WHERE id IN (:ids)', {
        replacements: { ids: createdIds.fnqs },
      });
    }
    if (createdIds.categories.length > 0) {
      await models.sequelize.query('DELETE FROM fnqCategories WHERE id IN (:ids)', {
        replacements: { ids: createdIds.categories },
      });
    }
    if (createdIds.system_account.length > 0) {
      await models.sequelize.query('DELETE FROM system_account WHERE system_account_id IN (:ids)', {
        replacements: { ids: createdIds.system_account },
      });
    }
    await models.sequelize.close();
  });

  describe('1. CRUD 기본 플로우', () => {
    let categoryId;

    test('1-1. 카테고리 생성', async () => {
      const res = await request(app)
        .post('/api/admin/fnqCategories')
        .set('Authorization', `Bearer ${sysToken}`)
        .send({ name: `${TEST_PREFIX}-카테고리`, corporationId: 1 })
        .expect(200);

      [categoryId] = res.body.ids;
      createdIds.categories.push(categoryId); // ID 추적
    });

    test('1-2. 카테고리 조회', async () => { /* categoryId 사용 */ });
    test('1-3. 카테고리 수정', async () => { /* categoryId 사용 */ });
    test('1-4. 카테고리 삭제', async () => {
      await request(app)
        .delete(`/api/admin/fnqCategories/${categoryId}`)
        .set('Authorization', `Bearer ${sysToken}`)
        .expect(200);
      // 삭제된 ID는 createdIds에서 제거 (afterAll에서 중복 삭제 방지)
      createdIds.categories = createdIds.categories.filter(id => id !== categoryId);
    });
  });
});
```

**특징**:
- 각 describe 내에서 test 순서가 의존적 (1-1에서 생성한 ID를 1-2에서 사용)
- API로 삭제한 리소스는 createdIds에서도 제거
- 에러 케이스는 별도 describe로 그룹핑

### 타입 B: 유저 저니

복잡한 비즈니스 로직을 가진 멀티스텝 워크플로우.

```javascript
const TEST_PREFIX = 'scenario.slimbody.score';

describe('슬림바디 챌린지 점수 시나리오', () => {
  let sysToken;
  let inbodyCard;
  let normalCard;
  const createdIds = {
    users: [], challenges: [], habitCards: [],
    habitPacks: [], system_account: [], account: [],
  };

  beforeAll(async () => {
    mockS3Uploader();
    // 어드민 + 공용 리소스 생성 (ID 추적)
  });

  afterAll(async () => {
    // FK 역순으로 자기 데이터만 DELETE
    // ...
    await models.sequelize.close();
  });

  describe('WF-01. 신규 참가자의 첫 인바디 등록', () => {
    let user, token, challengeId;

    beforeAll(async () => {
      user = await createTestUser({
        name: `${TEST_PREFIX}-WF01유저`,
        email: `${TEST_PREFIX}-wf01@test.com`,
        provider: 'atomy',
        snsId: `${TEST_PREFIX}-WF01`,
        corporationId: 1,
        birth: '19900101',
        gender: 2,
      });
      createdIds.users.push(user.id);
      token = generateUserToken(user.id);

      const result = await createChallengeViaApi({ sysToken, ... });
      challengeId = result.challengeId;
      createdIds.challenges.push(challengeId);

      await joinChallenge(challengeId, token);
    });

    test('1. 첫 인바디 측정 → 목표 체지방률 산정', async () => { ... });
    test('2. 7일 습관 완료 → 습관 점수 누적', async () => { ... });
  });

  describe('WF-02. 목표 달성 + 가산 점수', () => {
    // 독립된 유저, 챌린지로 테스트 (WF-01과 간섭 없음)
    let user, token, challengeId;

    beforeAll(async () => {
      user = await createTestUser({
        name: `${TEST_PREFIX}-WF02유저`,
        email: `${TEST_PREFIX}-wf02@test.com`,
        provider: 'atomy',
        snsId: `${TEST_PREFIX}-WF02`,
        corporationId: 1,
      });
      createdIds.users.push(user.id);
      // ...
    });
  });
});
```

**특징**:
- 각 WF가 독립된 유저와 데이터를 가짐 (WF 간 간섭 없음)
- 모든 WF의 데이터가 최상위 createdIds에 추적됨
- 날짜를 바꿔가며 withFakeDate로 시간 진행
- flush 함수로 스케줄러 동작 재현

### 타입 C: 인증/권한 플로우

인증, 토큰, 세션 관련 플로우.

```javascript
const TEST_PREFIX = 'scenario.auth.atomy';

describe('Atomy 로그인 시나리오', () => {
  let user;
  const createdIds = { users: [] };

  beforeAll(async () => {
    user = await createTestUser({
      name: `${TEST_PREFIX}-유저`,
      provider: 'atomy',
      snsId: `${TEST_PREFIX}-S0120000`,
      email: `${TEST_PREFIX}@test.com`,
    });
    createdIds.users.push(user.id);
  });

  afterAll(async () => {
    await models.sequelize.query('DELETE FROM users WHERE id IN (:ids)', {
      replacements: { ids: createdIds.users },
    });
    await models.sequelize.close();
  });

  test('유효한 ID로 로그인 성공', async () => { ... });
  test('로그인 후 보호된 API 접근 가능', async () => { ... });
});
```

## Helper 함수 패턴

### API 래퍼 함수

시나리오에서 반복 호출되는 API는 헬퍼 함수로 분리한다.

```javascript
/**
 * 어드민 API로 챌린지 생성
 * @throws {Error} 생성 실패 시 status + body 포함 에러
 * @returns {{ challengeId, packs }} 생성된 챌린지 ID와 팩 목록
 */
async function createChallengeViaApi({ sysToken, startDate, endDate, ...options }) {
  const res = await request(app)
    .post('/api/admin/challenge/create')
    .set('Authorization', `Bearer ${sysToken}`)
    .field('startDate', startDate)
    .field('endDate', endDate)
    // ...
  ;

  if (res.status !== 200) {
    throw new Error(`챌린지 생성 실패: ${res.status} ${JSON.stringify(res.body)}`);
  }

  // DB에서 생성 결과 조회 (API가 ID를 반환하지 않는 경우)
  const [rows] = await models.sequelize.query(
    `SELECT id FROM challenges WHERE id = (SELECT MAX(id) FROM challenges)`,
  );
  return { challengeId: rows[0].id };
}
```

**규칙**:
- 함수명: `{동작}{리소스}ViaApi` — `createChallengeViaApi`, `completeHabitViaApi`
- 실패 시 `throw new Error`로 즉시 중단 (어느 스텝에서 문제인지 빠르게 파악)
- API가 생성된 리소스 ID를 반환하지 않으면 DB 조회로 보완
- 파라미터는 객체 디스트럭처링으로 명확하게
- **createdIds에 push하는 것은 호출자의 책임** (헬퍼는 ID를 반환만 함)

### Flush 함수 (스케줄러 대체)

스케줄러가 주기적으로 실행하는 로직을 테스트에서 직접 호출한다.

```javascript
/**
 * 스케줄러의 점수 계산 로직을 직접 실행
 * 실서비스에서는 스케줄러가 주기적으로 이 로직을 실행하지만,
 * 테스트에서는 즉시 반영을 위해 직접 호출한다.
 */
async function flushSlimbodyScore({ userId, challengeId }) {
  // 스케줄러의 run() 로직에서 핵심 부분만 추출
  const pendingCompletes = await models.UserHabitCardComplete.findAll({
    where: { userId, isPending: true },
    // ...
  });

  // pending → confirmed 처리
  // 점수 재계산
}
```

**규칙**:
- flush 함수는 스케줄러의 핵심 로직만 추출 (로깅, 에러 핸들링 등은 제외)
- 함수 상단에 주석으로 "실서비스에서는 스케줄러가 실행" 설명
- 가능하면 스케줄러 소스에서 직접 export된 함수를 import하여 사용

## 로거 mock (전역 자동)

winston 로거는 `test/helpers/setupMocks.js`에서 **전역으로 자동 mock**된다. `jest.config.js`의 `setupFiles`에 등록되어 시나리오 테스트에서도 자동 적용된다. 개별 파일에 mock 코드를 추가할 필요가 없다.

**왜 전역 `moduleNameMapper`가 아닌 `setupFiles` 방식인가**: `moduleNameMapper`로 `./logger.js` 패턴을 매칭하면 `@sentry/utils` 내부 logger까지 같이 교체되어 `consoleSandbox` export가 사라져 Sentry가 SyntaxError로 죽는다. `jest.unstable_mockModule`은 resolved absolute path 기준이라 프로젝트 `src/logger.js`만 정확히 교체한다.

## 코드 템플릿

```javascript
import { jest } from '@jest/globals';
import request from 'supertest';
import app from '#src/app.js';
import models from '#src/db.js';
import {
  createTestUser,
  createTestAdminAccount,
  createTestSystemAccount,
  generateUserToken,
  generateAdminToken,
  generateSystemAdminToken,
  mockS3Uploader,
  TINY_PNG,
  withFakeDate,
} from '#test/helpers/fixtures.js';

// ─── TEST_PREFIX (파일명 기반 유니크 접두사) ───

const TEST_PREFIX = 'scenario.{domain}.{name}'; // 예: 'scenario.challenge.join'

// ─── Helper 함수 ───

async function createResourceViaApi({ token, ...params }) {
  const res = await request(app)
    .post('/api/...')
    .set('Authorization', `Bearer ${token}`)
    .send(params);
  if (res.status !== 200) {
    throw new Error(`리소스 생성 실패: ${res.status} ${JSON.stringify(res.body)}`);
  }
  return res.body;
}

// ─── 타임아웃 설정 (시나리오는 단위 테스트보다 오래 걸림) ───

jest.setTimeout(30000);

// ─── 메인 시나리오 ───

describe('시나리오: {시나리오명}', () => {
  // 공용 데이터 + 생성된 ID 추적
  let sysToken;
  const createdIds = {
    users: [],
    system_account: [],
    account: [],
    account_country: [],
    challenges: [],
    // ... 시나리오에서 사용하는 테이블별로 추가
  };

  beforeAll(async () => {
    mockS3Uploader(); // 파일 업로드가 있는 경우

    // 관리자 계정 + 공용 참조 데이터 생성
    const sysAccount = await createTestSystemAccount({
      system_account_uuid: `${TEST_PREFIX}-sys`,
      email: `${TEST_PREFIX}-sys@test.com`,
    });
    sysToken = generateSystemAdminToken(sysAccount.system_account_id);
    createdIds.system_account.push(sysAccount.system_account_id);
  });

  afterAll(async () => {
    // FK 역순으로 자기 데이터만 DELETE
    // 자식 테이블(FK가 있는) → 부모 테이블 순서
    const deleteOrder = [
      // ['테이블명', 'ID컬럼명', 'createdIds의 키']
      // 예시:
      // ['userHabitCardCompletes', 'id', 'userHabitCardCompletes'],
      // ['challengeUserMapping', 'id', 'challengeUserMapping'],
      // ['challenges', 'id', 'challenges'],
      ['system_account', 'system_account_id', 'system_account'],
      ['users', 'id', 'users'],
    ];

    for (const [table, idColumn, key] of deleteOrder) {
      const ids = createdIds[key];
      if (ids && ids.length > 0) {
        // eslint-disable-next-line no-await-in-loop
        await models.sequelize.query(
          `DELETE FROM \`${table}\` WHERE \`${idColumn}\` IN (:ids)`,
          { replacements: { ids } },
        );
      }
    }

    await models.sequelize.close();
  });

  // ─── WF-01. 기본 플로우 ───

  describe('WF-01. {워크플로우명}', () => {
    let user;
    let token;

    beforeAll(async () => {
      user = await createTestUser({
        name: `${TEST_PREFIX}-WF01유저`,
        email: `${TEST_PREFIX}-wf01@test.com`,
        provider: 'atomy',
        snsId: `${TEST_PREFIX}-WF01`,
        corporationId: 1,
      });
      token = generateUserToken(user.id);
      createdIds.users.push(user.id);
    });

    test('1. {첫 번째 스텝}', async () => {
      const res = await request(app)
        .post('/api/...')
        .set('Authorization', `Bearer ${token}`)
        .send({ ... });

      expect(res.status).toBe(200);
      // 생성된 리소스 ID 추적
      // createdIds.challenges.push(res.body.id);
    });

    test('2. {두 번째 스텝}', async () => {
      // 이전 스텝의 결과를 사용
    });

    test('3. {검증 스텝}', async () => {
      const res = await request(app)
        .get('/api/...')
        .set('Authorization', `Bearer ${token}`)
        .expect(200);

      expect(res.body.result).toBe(true);
    });
  });

  // ─── WF-02. 엣지 케이스 ───

  describe('WF-02. {엣지케이스 워크플로우}', () => {
    // 독립된 데이터로 테스트
    // createdIds는 최상위 공유 — 여기서 생성한 ID도 push
  });
});
```

## 인증 패턴

단위 테스트와 동일 (test/helpers/fixtures.js 사용):

```javascript
// 일반 유저
const user = await createTestUser({
  name: `${TEST_PREFIX}-유저`,
  email: `${TEST_PREFIX}@test.com`,
  provider: 'atomy',
  snsId: `${TEST_PREFIX}-001`,
  corporationId: 1,
});
createdIds.users.push(user.id);
const token = generateUserToken(user.id);

// 일반 어드민 (국가 권한)
const admin = await createTestAdminAccount({
  account_uuid: `${TEST_PREFIX}-admin`,
  email: `${TEST_PREFIX}-admin@test.com`,
  password: 'test',
  countryCodes: ['KR'],
});
createdIds.account.push(admin.account_id);
const adminToken = generateAdminToken(admin.account_id);

// 시스템 어드민 (전체 권한)
const sysAccount = await createTestSystemAccount({
  system_account_uuid: `${TEST_PREFIX}-sys`,
  email: `${TEST_PREFIX}-sys@test.com`,
});
createdIds.system_account.push(sysAccount.system_account_id);
const sysToken = generateSystemAdminToken(sysAccount.system_account_id);
```

## 날짜 조작 패턴

시나리오에서 날짜를 바꿔가며 진행하는 경우:

```javascript
test('1. 4/1 - 첫 습관 완료', async () => {
  await withFakeDate('2026-04-01', async () => {
    const res = await request(app)
      .post('/api/challenges/completeHabit')
      .set('Authorization', `Bearer ${token}`)
      .send({ challengeId, habitCardId });
    expect(res.status).toBe(200);
  });
});

test('2. 4/7 - 일주일 후 상태 확인', async () => {
  await withFakeDate('2026-04-07', async () => {
    const res = await request(app)
      .get(`/api/challenges/${challengeId}/status`)
      .set('Authorization', `Bearer ${token}`);
    expect(res.body.weeklyGoalMet).toBe(true);
  });
});
```

헬퍼 함수에 날짜를 넘기는 패턴:

```javascript
async function completeHabitViaApi({ token, challengeId, habitCardId, day }) {
  return withFakeDate(day, async () => {
    const res = await request(app)
      .post('/api/challenges/completeHabit')
      .set('Authorization', `Bearer ${token}`)
      .send({ challengeId, habitCardId });
    if (res.status !== 200) {
      throw new Error(`습관 완료 실패 (${day}): ${res.status}`);
    }
    return res;
  });
}
```

## 네이밍 규칙

- **파일명**: `{시나리오_설명}.spec.js` — `slimbody_score_test.spec.js`, `post_lifecycle.spec.js`
- **TEST_PREFIX**: `'scenario.{도메인}.{시나리오}'` — `'scenario.challenge.join'`, `'scenario.fnq.crud'`
- **최상위 describe**: `'시나리오: {시나리오명}'` 또는 `'{도메인} {설명} 시나리오'`
- **WF describe**: `'WF-{번호}. {워크플로우명}'`
- **test**: `'{순번}. {스텝 설명}'` 또는 `'{WF번호}-{순번}. {설명}'`

## 실행 방법

```bash
# 단일 시나리오 파일
yarn test test/scenarios/challenge/slimbody/slimbody_score_test.spec.js

# 도메인 전체 시나리오
yarn test test/scenarios/challenge/

# 전체 시나리오
yarn test test/scenarios/
```

## 시나리오 테스트 vs 단위 테스트 판단 기준

**시나리오 테스트로 작성해야 할 때**:
- API 2개 이상이 순서대로 호출되어야 의미가 있는 플로우
- 이전 API의 결과가 다음 API의 입력이 되는 경우
- 날짜를 바꿔가며 상태 변화를 추적해야 하는 경우
- 여러 유형의 유저(일반/어드민)가 참여하는 플로우
- 스케줄러가 중간에 개입하는 비즈니스 로직

**단위 테스트로 충분한 경우**:
- API 1개의 다양한 입력/에러 케이스
- 필드 검증, 인증 검증
- 단순 CRUD (복잡한 비즈니스 로직 없음)


<!-- 프로젝트 커스터마이징 (이 참고 구현을 자기 스택으로 교체할 때 바꿀 항목):
- import 구문: supertest / `#src/app.js` / `#src/db.js` / `#test/helpers/fixtures.js` → 자기 스택의 HTTP 클라이언트·앱 진입점·DB 핸들·픽스처
- 인증 헬퍼: createTestUser / createTestSystemAccount / generate*Token 등 → 프로젝트의 유저/어드민/시스템 토큰 생성 함수
- 원시 쿼리: `models.sequelize.query(...)` (MySQL) → 프로젝트 ORM/드라이버의 쿼리 API
- "사전 데이터는 API로 만든다" 원칙: 스택 무관하게 유지 — 시나리오 테스트의 존재 의의
- 데이터 격리(createdIds 추적 + FK 역순 자기 데이터만 삭제): 개념 보편, 삭제 코드만 자기 DB/ORM로
- FK/제약 규칙(6~11): MySQL/Sequelize 맥락 예시. 원칙(자식→부모, 전역 상태 불변, 필터 있는 count,
  스케줄러 job은 전용 격리)은 보편이므로 같은 결과를 내는 방법으로 옮긴다.
- flush 함수: 스케줄러/배치 핵심 로직을 직접 호출 — 가능하면 스케줄러 소스에서 export된 함수를 import
- 날짜 고정 유틸: withFakeDate → freezegun / fake clock 등
- 실행 명령: `yarn test test/scenarios/...` → 프로젝트 테스트 러너 명령
- 파일 위치/네이밍: `test/scenarios/{도메인}/{시나리오명}.spec.js` → 프로젝트 규칙
-->
