/*
 * 목업 공용 키트 — 스냅샷 HTML(또는 직접 그린 HTML) 맨 끝에 한 줄로 붙인다.
 *   <script src="../../_kit/mockup-kit.js"></script>
 *
 * 1) 상태 전환: <body data-states="asis,tobe,tobe-empty">
 *    요소에 data-show="tobe tobe-empty" → 그 상태에서만 보임 / data-hide="asis" → 그 상태에서 숨김
 *    ?state=tobe 로 열거나, 화면 아래 상태 바에서 고른다. 기본값은 첫 상태.
 * 2) 바뀌는 곳 표시: class="mk-new" data-note="설명" → 주황 점선 + NEW 태그
 *    태그가 위 요소에 가려지면 data-note-pos="bottom" 으로 아래에 붙인다
 *    class="mk-gone" → 빠지는 요소(asis 비교용, 빨간 점선 박스). tobe 상태에선 data-hide로 실제로 뺀다.
 * 3) ?capture=1 이면 상태 바를 숨긴다 (capture.mjs가 붙인다).
 */
(function () {
  // 손으로 쓴 목업에 viewport 메타가 없으면 모바일 캡처가 980px로 그려진다 → 없으면 넣는다
  if (!document.querySelector('meta[name="viewport"]')) {
    const m = document.createElement('meta');
    m.name = 'viewport';
    m.content = 'width=device-width, initial-scale=1';
    document.head.appendChild(m);
  }
  const q = new URLSearchParams(location.search);
  const states = (document.body.dataset.states || 'default').split(',').map((s) => s.trim());
  const state = q.get('state') || states[0];
  document.body.dataset.state = state;

  const font = 'system-ui, -apple-system, "Apple SD Gothic Neo", "Noto Sans KR", sans-serif';
  const css = `
    .mk-new { outline: 2px dashed #FF8A00 !important; outline-offset: 3px; position: relative; }
    .mk-new[data-note]::after {
      content: 'NEW · ' attr(data-note); position: absolute; top: -12px; right: 4px; z-index: 50;
      background: #FF8A00; color: #fff; font: 600 11px/1.6 ${font}; padding: 0 6px; border-radius: 4px; white-space: nowrap;
    }
    .mk-new:not([data-note])::after {
      content: 'NEW'; position: absolute; top: -12px; right: 4px; z-index: 50;
      background: #FF8A00; color: #fff; font: 700 11px/1.6 ${font}; padding: 0 6px; border-radius: 4px;
    }
    .mk-new[data-note-pos="bottom"]::after { top: auto; bottom: -12px; }
    .mk-gone { outline: 2px dashed #FF5C5C !important; outline-offset: 3px; opacity: .45; position: relative; }
    .mk-gone::after { content: '삭제'; position: absolute; top: -12px; right: 4px; background: #FF5C5C; color: #fff; font: 700 11px/1.6 ${font}; padding: 0 6px; border-radius: 4px; }
    #mk-state-bar { position: fixed; left: 50%; bottom: 16px; transform: translateX(-50%); z-index: 99999; display: flex; gap: 4px;
      background: #212529; padding: 6px; border-radius: 999px; box-shadow: 0 6px 20px rgba(0,0,0,.25); font: 600 13px ${font}; }
    #mk-state-bar a { color: #ADB5BD; padding: 6px 12px; border-radius: 999px; text-decoration: none; }
    #mk-state-bar a.on { background: #506CF5; color: #fff; }
  `;
  const style = document.createElement('style');
  style.textContent = css;
  document.head.appendChild(style);

  document.querySelectorAll('[data-show]').forEach((el) => {
    if (!el.dataset.show.split(/\s+/).includes(state)) el.style.display = 'none';
  });
  document.querySelectorAll('[data-hide]').forEach((el) => {
    if (el.dataset.hide.split(/\s+/).includes(state)) el.style.display = 'none';
  });

  if (q.get('capture') !== '1' && states.length > 1) {
    const bar = document.createElement('nav');
    bar.id = 'mk-state-bar';
    states.forEach((s) => {
      const a = document.createElement('a');
      a.href = `?state=${encodeURIComponent(s)}`;
      a.textContent = s;
      if (s === state) a.className = 'on';
      bar.appendChild(a);
    });
    document.body.appendChild(bar);
  }
})();
