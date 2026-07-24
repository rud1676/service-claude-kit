# 테스트 코드 컨벤션

> **이 문서는 "고쳐 쓰는 참고 구현"이다.** 아래 **핵심 원칙**(양산 금지·정당화·데이터 격리·자기 데이터만 삭제·전역 상태 불변·조건 있는 count 등)은 스택과 무관하게 **보편**이다. 반면 이후의 구체 코드는 **Node.js + Jest + supertest + Sequelize(MySQL)** 스택의 예시다 — 자기 프로젝트 스택(파이썬/고/자바 등)에 맞게 교체한다. 무엇을 바꿔야 하는지는 문서 맨 아래 `프로젝트 커스터마이징` 주석 참고.

이 참고 구현의 단위 테스트는 **실제 app 객체 + supertest + 실제 DB**로 API 1개를 테스트한다.
mock은 S3 업로더 등 외부 서비스만 한다. DB는 mock하지 않는다.

## 핵심 원칙

- **테스트 1개 = API 호출 1개**: 하나의 describe 블록이 하나의 엔드포인트를 담당
- **실제 DB 사용**: 테스트 DB에 데이터를 넣고, API를 호출하고, 응답과 DB 상태를 검증
- **인증 포함**: JWT 토큰을 생성해서 Authorization 헤더에 담아 호출
- **병렬 실행 안전**: 테스트 파일끼리 동시에 실행해도 서로 간섭하지 않아야 한다
- **양산 금지**: 모든 test 케이스는 "이 테스트가 없으면 어떤 버그를 놓치는가?"에 답할 수 있어야 한다
- **시나리오 테스트와 다른 점**: 시나리오는 여러 API를 순서대로 호출하며 상태를 쌓아감. 단위 테스트는 하나의 API에 대해 다양한 입력/상태를 검증

## 작성하지 않는 테스트

아래에 해당하면 테스트를 만들지 않는다:

- **인증 미들웨어 반복**: `토큰 없음 → 401`은 도메인당 1개 파일에서만 검증. 같은 미들웨어를 쓰는 다른 API에서 반복하지 않는다.
- **필드별 나열**: `name 누락 → 실패`, `email 누락 → 실패`, `title 누락 → 실패`처럼 같은 검증 로직을 필드마다 반복하지 않는다. 대표 1건으로 합친다.
- **프레임워크 동작**: Express의 JSON 파싱, Sequelize의 쿼리 생성 등 프레임워크가 보장하는 동작은 검증하지 않는다.
- **정당화 불가**: "이 테스트가 없으면 X 버그를 놓친다"를 설명할 수 없는 테스트는 삭제한다.
- **파일당 150줄 초과**: 테스트 파일이 150줄을 넘으면 케이스가 너무 많은 것. 중복을 줄이거나 정당화가 약한 것을 제거한다.

## 파일 위치

```
src/{도메인}/__test__/{리소스}.{동작}.test.js
```

파일 1개 = API 동작 1개. 리소스와 동작을 dot(.)으로 구분한다.

예시:
- `src/challenge/__test__/slimbody.getScores.test.js`
- `src/challenge/__test__/challenge.join.test.js`
- `src/community/__test__/post.create.test.js`
- `src/community/__test__/comment.add.test.js`
- `src/admin/community/__test__/admin.post.create.test.js` ← admin API는 `admin.` 접두사

기존 파일 참고 (동일한 네이밍 규칙):
- `src/community/controllers/__test__/post.create.spec.js`
- `src/community/controllers/__test__/comment.report.create.spec.js`
- `src/admin/community/controllers/__test__/admin.post.search.spec.js`

## 병렬 실행 안전 (데이터 격리)

**테스트는 병렬로 실행될 수 있다.** 다른 테스트 파일의 데이터를 건드리면 안 된다.

### 규칙 1: TRUNCATE 금지 — 자기 데이터만 DELETE

```javascript
// ❌ 절대 하지 않는다 — 다른 테스트가 사용 중인 데이터도 날아감
await models.sequelize.query('TRUNCATE TABLE users');

// ✅ 자기가 만든 데이터만 삭제
await models.sequelize.query('DELETE FROM posts WHERE userId = :userId', {
  replacements: { userId: user.id },
});
await models.sequelize.query('DELETE FROM users WHERE id = :id', {
  replacements: { id: user.id },
});
```

### 규칙 2: 고유한 식별자로 테스트 데이터 생성

테스트 파일마다 유니크한 접두사를 사용하여 데이터 충돌을 방지한다.

```javascript
// 파일명 기반 접두사 — 다른 테스트와 절대 겹치지 않음
const TEST_PREFIX = 'post.create';

const user = await createTestUser({
  name: `${TEST_PREFIX}-유저`,
  email: `${TEST_PREFIX}@test.com`,
  provider: 'atomy',
  snsId: `${TEST_PREFIX}-001`,
  corporationId: 1,
});
```

### 규칙 3: cleanup은 자기가 만든 ID 기준으로

beforeAll에서 생성한 데이터의 ID를 추적하고, afterAll에서 해당 ID만 삭제한다.

```javascript
describe('POST /api/posts (게시글 생성)', () => {
  const TEST_PREFIX = 'post.create';
  let user;
  let token;
  const createdIds = []; // 테스트 중 생성된 리소스 ID 추적

  beforeAll(async () => {
    mockS3Uploader();

    user = await createTestUser({
      name: `${TEST_PREFIX}-유저`,
      email: `${TEST_PREFIX}@test.com`,
      provider: 'atomy',
      snsId: `${TEST_PREFIX}-001`,
      corporationId: 1,
    });
    token = generateUserToken(user.id);
  });

  afterAll(async () => {
    // 테스트 중 생성된 리소스 정리
    if (createdIds.length > 0) {
      await models.sequelize.query(
        `DELETE FROM posts WHERE id IN (:ids)`,
        { replacements: { ids: createdIds } },
      );
    }
    // 사전 데이터 정리 (자기 유저만)
    await models.sequelize.query(
      'DELETE FROM users WHERE id = :id',
      { replacements: { id: user.id } },
    );
    await models.sequelize.close();
  });

  test('성공 - 게시글 생성', async () => {
    const res = await request(app)
      .post('/api/posts')
      .set('Authorization', `Bearer ${token}`)
      .send({ title: '테스트', content: '내용' })
      .expect(200);

    createdIds.push(res.body.postId); // 추적
    expect(res.body.result).toBe(true);
  });
});
```

### 규칙 4: 사전 데이터도 격리

참조 데이터(카테고리, 챌린지 등)를 만들 때도 테스트 전용으로 만들고, 자기 것만 정리한다.

### 규칙 5: `SET FOREIGN_KEY_CHECKS=0` 절대 금지

이걸 쓰고 부모 row(예: `habitCards`, `users`)를 삭제하면 FK CASCADE 가 꺼져 **자식 테이블(translations, histories)에 orphan 이 남는다**. 병렬 실행 중 다른 테스트가 새 부모 row 를 만들 때 auto-increment 가 orphan 의 FK 값과 겹치면 `UNIQUE(parentId, language)` 같은 제약에 걸려 **엉뚱한 테스트가 터진다**. cleanup 은 무조건 FK 순서대로 자식 → 부모로 DELETE 한다.

```javascript
// ❌ 금지 — orphan 생성, 다른 테스트 깨짐
await models.sequelize.query('SET FOREIGN_KEY_CHECKS=0');
await models.sequelize.query('DELETE FROM habitCards WHERE ...');
await models.sequelize.query('SET FOREIGN_KEY_CHECKS=1');

// ✅ 자식부터 순서대로
await models.sequelize.query('DELETE FROM habitCardsTranslations WHERE habitCardId IN (:ids)', { replacements: { ids } });
await models.sequelize.query('DELETE FROM habitCards WHERE id IN (:ids)', { replacements: { ids } });
```

### 규칙 6: Translation 생성 직전 방어적 `destroy`

과거 테스트 잔여 또는 FK_CHECKS=0 버그로 translation 테이블에 orphan 이 있을 수 있다. `(parentId, language)` UNIQUE 충돌을 피하기 위해 translation bulkCreate 직전 해당 parentId 로 destroy 한 번 호출한다.

```javascript
habitCard = await models.HabitCard.create({ ... });
createdIds.habitCards.push(habitCard.id);

// 방어적 orphan cleanup — 새 habitCard.id 로 된 잔여 translation 제거
await models.HabitCardTranslation.destroy({ where: { habitCardId: habitCard.id } });

await models.HabitCardTranslation.bulkCreate([
  { habitCardId: habitCard.id, language: 'ko', name: ... },
  { habitCardId: habitCard.id, language: 'en', name: ... },
]);
```

### 규칙 7: `count()` / `findAll()` 조건 없이 호출 금지

공유 테이블(pushes, externalApiLogs, users, corporations 등)에 조건 없이 `count()` 하면 다른 테스트가 만든 row 까지 세어져 결과가 비결정적이 된다. 항상 **이 테스트가 만든 row 만 세는 조건**을 붙인다.

```javascript
// ❌ 다른 테스트가 만든 row 까지 섞임
expect(await models.Push.count()).toBe(1);

// ✅ 이 테스트 job 의 특징 값으로 필터
expect(await models.Push.count({ where: { alarmType: ZERO_PUSH_ALARM_TYPE } })).toBe(1);
expect(await models.Push.count({ where: { toUserId: user.id } })).toBe(1);
```

### 규칙 8: 전역 DB 상태를 UPDATE 하지 않는다

`Corporation.update({isActive: false}, {where:{}})` 처럼 WHERE 없이 또는 내 테스트 대상이 아닌 row 까지 update 하면, 같은 시점 도는 다른 worker 의 테스트 전제를 깨뜨린다. DB 상태를 바꿀 거면 **내가 만든 row 만** 대상으로 하고, 다른 테스트가 의존하는 seed row(`Corporation.isActive`, 시스템 유저 id=1 등)는 건드리지 않는다.

전역 조회 결과를 제어하고 싶으면 DB 가 아니라 **코드 레벨 monkey-patch** 를 쓴다. worker 프로세스 단위라 다른 worker 에 영향이 없다.

```javascript
// ❌ DB 전역 상태 변경 — 다른 worker 의 API 호출에 영향
await models.Corporation.update({ isActive: false }, { where: {} });

// ✅ 이 테스트 파일에서만 유효한 monkey-patch
let originalFindAll;
function installFindAllPatch() {
  originalFindAll = models.Corporation.findAll.bind(models.Corporation);
  models.Corporation.findAll = async (opts) => {
    if (opts?.where?.isActive === true) return activeCorps; // 테스트 전용 corp 만 리턴
    return originalFindAll(opts);
  };
}
function uninstallFindAllPatch() {
  if (originalFindAll) {
    models.Corporation.findAll = originalFindAll;
    originalFindAll = null;
  }
}
// beforeAll 에서 install, afterAll 에서 uninstall
```

```javascript
let categoryId;

beforeAll(async () => {
  // 이 테스트 전용 카테고리
  const [result] = await models.sequelize.query(
    `INSERT INTO postCategories (name, createdAt, updatedAt) VALUES (:name, NOW(), NOW())`,
    { replacements: { name: `${TEST_PREFIX}-카테고리` } },
  );
  categoryId = result;
});

afterAll(async () => {
  await models.sequelize.query(
    'DELETE FROM postCategories WHERE id = :id',
    { replacements: { id: categoryId } },
  );
});
```

## 로거 mock (전역 자동)

winston 로거는 `test/helpers/setupMocks.js`에서 **전역으로 자동 mock**된다. `jest.config.js`의 `setupFiles`에 등록되어 모든 테스트 파일에서 자동 적용된다. 테스트 파일에서 별도 mock을 작성할 필요가 **없다**.

**왜 전역 `moduleNameMapper`가 아닌 `setupFiles` + `jest.unstable_mockModule`인가**:
- `moduleNameMapper`로 `^(\\.{1,2}/)+logger\\.js$` 같은 정규식을 쓰면 `@sentry/utils` 내부의 `./logger.js` import까지 매칭되어 `consoleSandbox` export가 사라져 Sentry가 SyntaxError로 죽는다.
- `jest.unstable_mockModule`은 **resolved absolute path**를 기준으로 mock을 등록하므로 프로젝트의 `src/logger.js`만 정확히 교체하고 Sentry 내부 logger는 건드리지 않는다.
- `setupFiles`는 각 테스트 파일의 import가 실행되기 전에 돌아가므로 중앙 1회 등록으로 모든 테스트에 적용된다.

만약 테스트에서 logger의 호출을 assertion하고 싶다면 (예: `expect(logger.warn).toHaveBeenCalledWith(...)`), 다음처럼 import하여 사용:

```javascript
import logger from '#src/logger.js';
// logger.warn, logger.error 등은 jest.fn() 스텁이므로 mockClear(), toHaveBeenCalled* 모두 사용 가능
```

## 코드 템플릿

```javascript
import request from 'supertest';
import app from '#src/app.js';
import models from '#src/db.js';
import {
  createTestUser,
  createTestAdminAccount,
  generateUserToken,
  generateAdminToken,
  mockS3Uploader,
  TINY_PNG,
  withFakeDate,
} from '#test/helpers/fixtures.js';

const TEST_PREFIX = 'resource.action'; // 파일명과 동일하게

const BASE_URL = '/api/target-resource';

describe('GET /api/target-resource/:id (리소스 조회)', () => {
  let user;
  let token;

  beforeAll(async () => {
    mockS3Uploader(); // 파일 업로드가 있는 경우

    // 테스트 유저 생성 + 토큰
    user = await createTestUser({
      name: `${TEST_PREFIX}-유저`,
      email: `${TEST_PREFIX}@test.com`,
      provider: 'atomy',
      snsId: `${TEST_PREFIX}-001`,
      corporationId: 1,
    });
    token = generateUserToken(user.id);

    // 테스트에 필요한 사전 데이터 세팅
  });

  afterAll(async () => {
    // 자기가 만든 데이터만 정리
    await models.sequelize.query(
      'DELETE FROM users WHERE id = :id',
      { replacements: { id: user.id } },
    );
    await models.sequelize.close();
  });

  test('성공 - 정상 조회', async () => {
    const res = await request(app)
      .get(`${BASE_URL}/1`)
      .set('Authorization', `Bearer ${token}`)
      .expect(200);

    expect(res.body.result).toBe(true);
  });

  test('실패 - 토큰 없음 (401)', async () => {
    await request(app)
      .get(`${BASE_URL}/1`)
      .expect(401);
  });
});
```

## 인증 패턴

### 일반 유저

```javascript
const user = await createTestUser({
  name: `${TEST_PREFIX}-유저`,
  email: `${TEST_PREFIX}@test.com`,
  provider: 'atomy',
  snsId: `${TEST_PREFIX}-001`,
  corporationId: 1,
  birth: '19900101',  // 필요한 경우
  gender: 2,          // 필요한 경우
});
const token = generateUserToken(user.id);

// 요청 시
request(app)
  .get('/api/some-endpoint')
  .set('Authorization', `Bearer ${token}`)
```

### 일반 어드민 (국가 권한 있음)

```javascript
const admin = await createTestAdminAccount({
  account_uuid: `${TEST_PREFIX}-admin`,
  email: `${TEST_PREFIX}-admin@test.com`,
  password: 'test',
  countryCodes: ['KR'],
});
const adminToken = generateAdminToken(admin.account_id);

// 요청 시
request(app)
  .get('/api/admin/some-endpoint')
  .set('Authorization', `Bearer ${adminToken}`)
```

### 시스템 어드민 (전체 권한)

```javascript
import { createTestSystemAccount, generateSystemAdminToken } from '../../helpers/fixtures.js';

const sysAccount = await createTestSystemAccount({
  system_account_uuid: `${TEST_PREFIX}-sys`,
  email: `${TEST_PREFIX}-sys@test.com`,
});
const sysToken = generateSystemAdminToken(sysAccount.system_account_id);
```

## 요청 패턴

### JSON body (POST/PUT)

```javascript
const res = await request(app)
  .post(`${BASE_URL}`)
  .set('Authorization', `Bearer ${token}`)
  .send({ field1: 'value1', field2: 123 })
  .expect(200);
```

### multipart/form-data (파일 업로드 포함)

```javascript
const res = await request(app)
  .post(`${BASE_URL}`)
  .set('Authorization', `Bearer ${token}`)
  .field('title', '제목')
  .field('content', '내용')
  .attach('image', TINY_PNG, 'test.png')
  .expect(200);
```

### query string (GET)

```javascript
const res = await request(app)
  .get(`${BASE_URL}?page=1&limit=10&search=keyword`)
  .set('Authorization', `Bearer ${token}`)
  .expect(200);
```

## 날짜 조작이 필요한 경우

API가 현재 날짜 기준으로 동작할 때 `withFakeDate`를 사용:

```javascript
test('성공 - 챌린지 기간 내 요청', async () => {
  const res = await withFakeDate('2026-04-05', async () => {
    return request(app)
      .post(`${BASE_URL}/complete`)
      .set('Authorization', `Bearer ${token}`)
      .send({ challengeId, habitCardId })
  });

  expect(res.status).toBe(200);
});
```

## 사전 데이터 세팅 패턴

### 방법 1: DB 직접 INSERT (간단한 참조 데이터)

```javascript
// 테이블에 직접 넣기
const [insertId] = await models.sequelize.query(
  `INSERT INTO someTable (name, status) VALUES (:name, :status)`,
  { replacements: { name: `${TEST_PREFIX}-데이터`, status: 1 } },
);
// insertId를 저장해두고 afterAll에서 DELETE
```

### 방법 2: API 호출로 세팅 (복잡한 데이터, 연관관계 있을 때)

```javascript
// 어드민 API로 챌린지 생성 → 실제 비즈니스 로직이 연관 데이터도 함께 만듦
const res = await request(app)
  .post('/api/admin/challenge/create')
  .set('Authorization', `Bearer ${sysToken}`)
  .field('name', '테스트 챌린지')
  .field('startDate', '2026-04-01')
  // ...
  .expect(200);
// 생성된 ID를 추적하여 afterAll에서 정리
```

### 방법 3: 모델 직접 사용

```javascript
const record = await models.SomeModel.create({
  userId: user.id,
  value: 100,
});
// record.id를 추적
```

## Assertion 패턴

### 응답 body 검증

```javascript
// 필수 필드 존재 확인
expect(res.body.result).toBe(true);
expect(res.body.data).toBeDefined();

// 구체적 값 비교
expect(res.body.data.score).toBe(70);
expect(res.body.data.rate).toBeCloseTo(23.371, 2);

// 배열 길이
expect(res.body.rows).toHaveLength(3);

// 객체 일부 필드만
expect(res.body.data).toEqual(
  expect.objectContaining({ id: 1, status: 'active' }),
);
```

### DB 상태 검증 (API 호출 후 side-effect 확인)

```javascript
// API 호출 후 DB에 실제로 저장되었는지 확인
const [rows] = await models.sequelize.query(
  'SELECT * FROM targetTable WHERE userId = :userId',
  { replacements: { userId: user.id } },
);
expect(rows).toHaveLength(1);
expect(rows[0].status).toBe('completed');
```

## 네이밍 규칙

- **파일명**: `{리소스}.{동작}.test.js` — `post.create.test.js`, `slimbody.getScores.test.js`
  - admin API: `admin.{리소스}.{동작}.test.js` — `admin.post.create.test.js`
- **TEST_PREFIX**: 파일명과 동일 — `const TEST_PREFIX = 'post.create'`
- **describe**: `'{METHOD} {URL} (한글 설명)'` — `'GET /api/slimbody/:id/scores (슬림바디 점수 조회)'`
- **test 성공**: `'성공 - {구체적 상황}'`
- **test 실패**: `'실패 - {에러 상황}'`

## 실행 방법

```bash
# 단일 파일
NODE_ENV=test node --experimental-vm-modules node_modules/jest/bin/jest.js --forceExit src/challenge/__test__/slimbody.getScores.test.js

# 도메인 전체
NODE_ENV=test node --experimental-vm-modules node_modules/jest/bin/jest.js --forceExit src/challenge/__test__/
```


<!-- 프로젝트 커스터마이징 (이 참고 구현을 자기 스택으로 교체할 때 바꿀 항목):
- import 구문: supertest / `#src/app.js` / `#src/db.js` / `#test/helpers/fixtures.js` → 자기 스택의 HTTP 클라이언트·앱 진입점·DB 핸들·픽스처
- 인증 헬퍼: createTestUser / createTestAdminAccount / generateUserToken 등 → 프로젝트의 토큰·세션 생성 함수
- 원시 쿼리: `models.sequelize.query(...)` (MySQL) → 프로젝트 ORM/드라이버의 쿼리 API
- 데이터 격리 메커니즘: TEST_PREFIX 접두사 + 자기 ID만 DELETE → 스택 무관하게 유지(개념이 보편)
- FK/제약 관련 규칙(5~8): FOREIGN_KEY_CHECKS·translation orphan·전역 UPDATE·조건 없는 count는
  MySQL/Sequelize 맥락의 예시다. 원칙("자식→부모 순 삭제, 전역 상태 불변, 필터 있는 count")은 보편이므로,
  자기 DB/ORM에서 같은 결과를 내는 방법으로 옮긴다.
- 로거 mock (setupFiles + jest.unstable_mockModule): Jest+winston+Sentry 특정 이슈다. 다른 러너/로거면 그
  러너의 전역 setup 방식으로 대체(원칙: 로거 mock은 파일마다 반복하지 말고 중앙 1회).
- 날짜 고정 유틸: withFakeDate → freezegun / fake clock 등
- 실행 명령: `yarn test ...` / `node --experimental-vm-modules ... jest` → 프로젝트 테스트 러너 명령
- 파일 위치/네이밍: `src/{도메인}/__test__/{리소스}.{동작}.test.js` → 프로젝트 규칙
-->
