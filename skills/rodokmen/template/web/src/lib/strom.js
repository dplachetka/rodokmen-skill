// Interaktivní stromový graf předků (rodiče nad dítětem, rozbalování větví, příbuzní ze SIDE vedle předka).
// Používá ho stránka /strom/ (src/pages/strom.astro) i tools/jeden_soubor.py, který tenhle soubor vloží do HTML
// (proto čistý JavaScript bez novějších zkratek ?. ?? Object.hasOwn – kvůli starším mobilním prohlížečům).
//
// stromovyGraf({ N, stage, buttons, hash }):
//   N        uzly podle Kekulého čísla: { s: odkaz, n: jméno, y: roky, c: barva rodu, a: 1 = předek vícekrát,
//            fu: 1 = otec neuveden, b: stav hledání sourozenců, sd: [{ n, r, y, kind, t, f, st, z: [[odkaz, datum]] }] }
//   stage    prvek se třídou tree-stage (uvnitř .tree-canvas se svg.tree-lines a .tree-info)
//   buttons  prvek s tlačítky [data-act=open|close|fit|root]
//   hash     true = stav (kořen, rozbalené větve) v adrese stránky, aby šel sdílet; false = adresu nechat být
// Vrací { zobrazOd(k) } – přestaví strom od předka k.
export function stromovyGraf(o) {
  var N = o.N, stage = o.stage, useHash = o.hash !== false;
  var canvas = stage.querySelector('.tree-canvas');
  var lines = canvas.querySelector('svg');
  var info = stage.querySelector('.tree-info');
  var CW = 168, CH = 62, SW = 150, GAP = 22, ROW = 130, SIDE_GAP = 14;
  var has = function (k) { return Object.prototype.hasOwnProperty.call(N, k); };
  var gen = function (k) { return Math.floor(Math.log2(k)); };
  var esc = function (t) {
    return String(t).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; });
  };

  // stav: kořen, rozbalení předci, otevřené skupiny příbuzných
  var ids = function (v) { return new Set((v || '').split('.').filter(Boolean).map(Number)); };
  var hasPar = function (k) { return !!N[k] && !N[k].a && !!(N[2 * k] || N[2 * k + 1]); };
  var known = function (k) { return N[k] && !N[k].a ? 1 + known(2 * k) + known(2 * k + 1) : N[k] ? 1 : 0; };
  var all = function (k, out) {
    out = out || [];
    if (hasPar(k)) { out.push(k); all(2 * k, out); all(2 * k + 1, out); }
    return out;
  };
  var root = 1, open = new Set(), sib = new Set();
  var defaults = function () { open = new Set(all(root).filter(function (k) { return gen(k) - gen(root) < 3; })); sib = new Set(); };
  var readHash = function () {
    var hp = new URLSearchParams(location.hash.slice(1));
    var k = hp.get('k') || '';
    root = /^\d+$/.test(k) && has(k) ? Number(k) : 1;
    if (hp.has('o')) open = ids(hp.get('o')); else defaults();
    sib = ids(hp.get('s'));
  };
  var save = function () {
    if (useHash) history.replaceState(null, '', '#k=' + root + '&o=' + Array.from(open).join('.') + '&s=' + Array.from(sib).join('.'));
  };

  // rozložení: rozsah vlevo a vpravo od středu karty; páry tak, aby se jejich podstromy nepřekrývaly
  // příbuzní jdou na vnější stranu páru: otcovi vlevo, matčini vpravo
  var rightSide = function (k) { return k !== root && k % 2 === 1; };
  var sideW = function (k) { return sib.has(k) && N[k] && N[k].sd.length ? N[k].sd.length * (SW + 8) + 8 : 0; };
  var ext = {};
  var measure = function (k) {
    var sw = sideW(k), extra = sw ? sw + SIDE_GAP : 0;
    var L = CW / 2 + (rightSide(k) ? 0 : extra), R = CW / 2 + (rightSide(k) ? extra : 0), D = 0;
    if (open.has(k) && hasPar(k)) {
      var f = N[2 * k] ? measure(2 * k) : { L: CW / 2, R: CW / 2 };
      var m = N[2 * k + 1] ? measure(2 * k + 1) : { L: CW / 2, R: CW / 2 };
      D = f.R + GAP + m.L;
      L = Math.max(L, D / 2 + f.L);
      R = Math.max(R, D / 2 + m.R);
    }
    ext[k] = { L: L, R: R, D: D };
    return { L: L, R: R };
  };
  var pos = {};
  var place = function (k, x, y) {
    pos[k] = { x: x, y: y };
    var D = ext[k] ? ext[k].D : 0;
    if (D) { place(2 * k, x - D / 2, y - ROW); place(2 * k + 1, x + D / 2, y - ROW); }
  };

  var sibLabel = function (k) {
    var p = N[k], n = p.sd.length;
    if (n) {
      var sibs = p.sd.filter(function (e) { return e.kind === 'sib'; }).length;
      var word = sibs === n ? 'sourozenci' : sibs ? 'sourozenci a další' : 'příbuzní a další';
      return '<button type="button" class="tc-sib' + (p.b === 'done' ? '' : ' todo') + '" data-sib="' + k + '" title="' +
        (p.b === 'done' ? 'Sourozenci dohledáni' : 'Sourozenci možná nejsou všichni') + '">' + (sib.has(k) ? '▾' : '▸') + ' ' + word + ' (' + n + ')</button>';
    }
    return '<span class="tc-sib none">' + (p.b === 'done' ? 'bez sourozenců' : p.b === 'partial' ? 'sourozenci: hledáno částečně' : 'sourozenci nehledáni') + '</span>';
  };

  var view = { s: 1, tx: 0, ty: 0 };
  var applyView = function () { canvas.style.transform = 'translate(' + view.tx + 'px,' + view.ty + 'px) scale(' + view.s + ')'; };
  var off = { x: 0, y: 0 }, size = { w: 0, h: 0 };

  var render = function () {
    var k;
    for (k in ext) delete ext[k];
    for (k in pos) delete pos[k];
    measure(root);
    place(root, 0, 0);
    var ks = Object.keys(pos).map(Number);
    var L = function (k) { return ext[k] ? ext[k].L : CW / 2; }, R = function (k) { return ext[k] ? ext[k].R : CW / 2; };
    var minX = Math.min.apply(null, ks.map(function (k) { return pos[k].x - L(k); }));
    var maxX = Math.max.apply(null, ks.map(function (k) { return pos[k].x + R(k); }));
    var minY = Math.min.apply(null, ks.map(function (k) { return pos[k].y; })) - 20;
    off = { x: 20 - minX, y: 20 - minY };
    size = { w: maxX - minX + 40, h: -minY + CH + 40 };
    var X = function (x) { return x + off.x; }, Y = function (y) { return y + off.y; };

    var html = '', svg = '';
    ks.forEach(function (k) {
      var p = N[k], x = pos[k].x, y = pos[k].y;
      var left = X(x - CW / 2), top = Y(y);
      if (!p) {
        var label = k % 2 === 0 && N[k >> 1] && N[k >> 1].fu ? 'otec neuveden' : 'zatím neznámý';
        html += '<div class="tc-card tc-unk" style="left:' + left + 'px;top:' + top + 'px">?<span class="tc-y">' + label + '</span></div>';
        return;
      }
      var tog = hasPar(k)
        ? '<button type="button" class="tc-tog" data-tog="' + k + '" aria-expanded="' + open.has(k) + '" title="' +
          (open.has(k) ? 'Sbalit předky' : 'Rozbalit předky') + '">' + (open.has(k) ? '−' : '+' + (known(k) - 1)) + '</button>'
        : '';
      html += '<div class="tc-card' + (k === root ? ' tc-root' : '') + (p.a ? ' tc-alias' : '') + '" style="left:' + left + 'px;top:' + top + 'px' +
        (p.c ? ';border-left-color:' + p.c : '') + '">' + tog + '<a href="' + esc(p.s) + '" draggable="false">' + esc(p.n) + '</a>' +
        '<span class="tc-y">' + (p.a ? 'předek vícekrát – viz výše' : esc(p.y || ' ')) + '</span>' + (k === 1 || p.a ? '' : sibLabel(k)) + '</div>';
      var sw = sideW(k);
      if (sw) {
        var sx = rightSide(k) ? X(x + CW / 2 + SIDE_GAP) : X(x - CW / 2 - SIDE_GAP - sw);
        html += '<div class="tc-sides" style="left:' + sx + 'px;top:' + top + 'px;width:' + sw + 'px">' + p.sd.map(function (e, i) {
          return '<button type="button" class="tc-side" data-side="' + k + ':' + i + '"><strong>' + esc(e.n) + '</strong><span>' +
            esc(e.r) + (e.y ? ' · ' + esc(e.y) : '') + '</span></button>';
        }).join('') + '</div>';
        var x1 = rightSide(k) ? left + CW : sx + sw, x2 = rightSide(k) ? sx : left;
        svg += '<line class="dash" x1="' + x1 + '" y1="' + (top + CH / 2) + '" x2="' + x2 + '" y2="' + (top + CH / 2) + '"/>';
      }
      var D = ext[k] ? ext[k].D : 0;
      if (D) {
        var py = Y(y - ROW) + CH / 2;
        svg += '<path d="M' + X(x - D / 2 + CW / 2) + ' ' + py + 'H' + X(x + D / 2 - CW / 2) + 'M' + X(x) + ' ' + py + 'V' + top + '"/>';
      }
    });
    Array.prototype.forEach.call(canvas.querySelectorAll('.tc-card,.tc-sides'), function (e) { e.parentNode.removeChild(e); });
    canvas.insertAdjacentHTML('beforeend', html);
    lines.setAttribute('width', String(size.w));
    lines.setAttribute('height', String(size.h));
    lines.innerHTML = svg;
    canvas.style.width = size.w + 'px';
    canvas.style.height = size.h + 'px';
    var rb = o.buttons.querySelector('[data-act=root]');
    if (rb) rb.hidden = root === 1;
    save();
  };

  var fit = function () {
    var r = stage.getBoundingClientRect();
    var s = Math.min(1, (r.width - 20) / size.w, (r.height - 20) / size.h);
    var z = Math.max(s, 0.08);
    view = { s: z, tx: (r.width - size.w * z) / 2, ty: Math.max(10, (r.height - size.h * z) / 2) };
    applyView();
  };
  // první pohled: celý strom, na malé obrazovce čitelný kořen dole
  var start = function () {
    fit();
    if (view.s >= 0.5) return;
    var r = stage.getBoundingClientRect(), z = 0.7;
    view = { s: z, tx: r.width / 2 - (pos[root].x + off.x) * z, ty: r.height - 30 - (pos[root].y + off.y + CH) * z };
    applyView();
  };
  // překreslit a nechat kartu k na stejném místě obrazovky
  var rerender = function (k) {
    var before = pos[k] && { x: (pos[k].x + off.x) * view.s, y: (pos[k].y + off.y) * view.s };
    render();
    if (before && pos[k]) { view.tx += before.x - (pos[k].x + off.x) * view.s; view.ty += before.y - (pos[k].y + off.y) * view.s; }
    applyView();
  };

  var zoomAt = function (f, cx, cy) {
    var r = stage.getBoundingClientRect();
    var s = Math.min(2.5, Math.max(0.08, view.s * f)), px = cx - r.left, py = cy - r.top;
    view = { s: s, tx: px - (px - view.tx) * (s / view.s), ty: py - (py - view.ty) * (s / view.s) };
    applyView();
  };
  stage.addEventListener('wheel', function (e) {
    if (info.contains(e.target)) return;
    e.preventDefault(); zoomAt(e.deltaY < 0 ? 1.15 : 0.87, e.clientX, e.clientY);
  }, { passive: false });

  // tažením posun (myš i prst), dvěma prsty přiblížení
  var pts = new Map(), moved = 0, pinch = 0;
  stage.addEventListener('pointerdown', function (e) { moved = 0; if (info.contains(e.target)) return; pts.set(e.pointerId, { x: e.clientX, y: e.clientY }); });
  stage.addEventListener('pointermove', function (e) {
    var prev = pts.get(e.pointerId);
    if (!prev) return;
    pts.set(e.pointerId, { x: e.clientX, y: e.clientY });
    if (pts.size === 2) {
      var ab = Array.from(pts.values()), a = ab[0], b = ab[1];
      var d = Math.hypot(a.x - b.x, a.y - b.y);
      if (pinch) zoomAt(d / pinch, (a.x + b.x) / 2, (a.y + b.y) / 2);
      pinch = d; moved += 10;
      return;
    }
    var dx = e.clientX - prev.x, dy = e.clientY - prev.y;
    moved += Math.abs(dx) + Math.abs(dy);
    if (moved > 4) { stage.setPointerCapture(e.pointerId); view.tx += dx; view.ty += dy; applyView(); }
  });
  var up = function (e) { pts.delete(e.pointerId); if (pts.size < 2) pinch = 0; };
  stage.addEventListener('pointerup', up);
  stage.addEventListener('pointercancel', up);

  stage.addEventListener('click', function (e) {
    if (moved > 4 && e.detail > 0) { e.preventDefault(); e.stopPropagation(); return; }
    var t = e.target.closest('[data-tog],[data-sib],[data-side],[data-close]');
    if (!t) return;
    var k;
    if (t.dataset.tog) {
      k = Number(t.dataset.tog);
      if (open.has(k)) open.delete(k); else open.add(k);
      rerender(k);
    } else if (t.dataset.sib) {
      k = Number(t.dataset.sib);
      if (sib.has(k)) sib.delete(k); else sib.add(k);
      rerender(k);
    } else if (t.dataset.side) {
      var ki = t.dataset.side.split(':').map(Number), e2 = N[ki[0]].sd[ki[1]];
      info.innerHTML = '<button type="button" class="tree-info-x" data-close aria-label="Zavřít">×</button>' +
        '<strong>' + esc(e2.n) + '</strong> <span class="muted">' + esc(e2.r) + (e2.y ? ' · ' + esc(e2.y) : '') + ' – ' + esc(N[ki[0]].n) + '</span>' +
        (e2.st ? '<p class="small muted">' + esc(e2.st) + '</p>' : '') +
        (e2.f.length ? '<ul class="small">' + e2.f.map(function (x) { return '<li>' + esc(x) + '</li>'; }).join('') + '</ul>' : '') +
        (e2.t ? '<p>' + esc(e2.t) + '</p>' : '') +
        (e2.z.length ? '<p class="small">Zápisy: ' + e2.z.map(function (z) { return '<a href="' + esc(z[0]) + '">' + esc(z[1]) + '</a>'; }).join(' · ') + '</p>' : '');
      info.hidden = false;
    } else {
      info.hidden = true;
    }
  }, true);

  Array.prototype.forEach.call(o.buttons.querySelectorAll('button[data-act]'), function (b) {
    b.addEventListener('click', function () {
      var act = b.dataset.act;
      if (act === 'open') { open = new Set(all(root)); render(); fit(); }
      else if (act === 'close') { open = new Set([root]); render(); fit(); }
      else if (act === 'root') { root = 1; defaults(); render(); fit(); }
      else fit();
    });
  });

  if (useHash) {
    window.addEventListener('hashchange', function () { readHash(); render(); start(); });
    readHash();
  } else {
    defaults();
  }
  render();
  start();
  return {
    zobrazOd: function (k) {
      root = has(k) && !N[k].a ? Number(k) : 1;
      defaults(); render(); start();
    },
  };
}
