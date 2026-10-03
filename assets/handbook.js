// Engineering Handbooks: page behaviour shared by the three books.
(function () {
  "use strict";
  var printMode = /[?&]print\b/.test(location.search);

  // Code: highlight, then add a gutter with the file's own line numbers.
  document.querySelectorAll("pre.code").forEach(function (pre) {
    var code = pre.querySelector("code");
    if (!code) return;
    if (window.hljs && !/language-(text|plaintext)/.test(code.className)) {
      try { window.hljs.highlightElement(code); } catch (e) { /* plain text is fine */ }
    }
    var first = parseInt((pre.dataset.lines || "1").split("-")[0], 10) || 1;
    var count = code.textContent.replace(/\n$/, "").split("\n").length;
    var nums = [];
    for (var i = 0; i < count; i++) nums.push(first + i);
    var gutter = document.createElement("span");
    gutter.className = "ln";
    gutter.setAttribute("aria-hidden", "true");
    gutter.textContent = nums.join("\n");
    pre.insertBefore(gutter, code);
  });

  // Print edition: deep dives open, and each chapter's answers gathered after its questions.
  function preparePrint() {
    document.querySelectorAll("details.deep").forEach(function (d) { d.open = true; });
    document.querySelectorAll("ol.qs").forEach(function (ol) {
      if (ol.nextElementSibling && ol.nextElementSibling.classList.contains("answers-print")) return;
      var box = document.createElement("div");
      box.className = "answers-print";
      var h = document.createElement("h4");
      h.textContent = "Answers";
      box.appendChild(h);
      var list = document.createElement("ol");
      list.className = "answers-list";
      ol.querySelectorAll(":scope > li").forEach(function (li) {
        var a = li.querySelector(".ans p");
        var item = document.createElement("li");
        item.innerHTML = a ? a.innerHTML : "";
        list.appendChild(item);
      });
      box.appendChild(list);
      ol.after(box);
    });
  }
  if (printMode) preparePrint();
  window.addEventListener("beforeprint", preparePrint);

  // Contents rail: mark the section in view.
  var links = Array.prototype.slice.call(document.querySelectorAll(".toc a[href^='#']"));
  if (links.length && "IntersectionObserver" in window) {
    var byId = {};
    links.forEach(function (a) { byId[a.getAttribute("href").slice(1)] = a; });
    var obs = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (!en.isIntersecting) return;
        var a = byId[en.target.id];
        if (!a) return;
        links.forEach(function (l) { l.classList.remove("is-current"); });
        a.classList.add("is-current");
      });
    }, { rootMargin: "0px 0px -75% 0px" });
    Object.keys(byId).forEach(function (id) {
      var el = document.getElementById(id);
      if (el) obs.observe(el);
    });
  }

  // Line charts: a crosshair and a readout of every series at the hovered x.
  document.querySelectorAll(".chart-wrap[data-chart]").forEach(function (wrap) {
    var spec;
    try { spec = JSON.parse(wrap.dataset.chart); } catch (e) { return; }
    var svg = wrap.querySelector("svg");
    if (!svg) return;
    var tip = document.createElement("div");
    tip.className = "chart-tip";
    tip.hidden = true;
    wrap.appendChild(tip);
    var ns = "http://www.w3.org/2000/svg";
    var line = document.createElementNS(ns, "line");
    line.setAttribute("class", "xhair");
    line.setAttribute("y1", spec.plot.y0);
    line.setAttribute("y2", spec.plot.y1);
    line.style.display = "none";
    svg.appendChild(line);
    var dots = spec.series.map(function (s) {
      var c = document.createElementNS(ns, "circle");
      c.setAttribute("r", "4.5");
      c.setAttribute("class", s.fill + " ring");
      c.style.display = "none";
      svg.appendChild(c);
      return c;
    });
    function toX(n) { return spec.plot.x0 + (Math.log10(n) - spec.logMin) / (spec.logMax - spec.logMin) * (spec.plot.x1 - spec.plot.x0); }
    function toY(v) { return spec.plot.y1 - v * (spec.plot.y1 - spec.plot.y0); }
    function move(ev) {
      var pt = svg.createSVGPoint();
      pt.x = ev.clientX; pt.y = ev.clientY;
      var p = pt.matrixTransform(svg.getScreenCTM().inverse());
      if (p.x < spec.plot.x0 || p.x > spec.plot.x1) { hide(); return; }
      var lg = spec.logMin + (p.x - spec.plot.x0) / (spec.plot.x1 - spec.plot.x0) * (spec.logMax - spec.logMin);
      var n = Math.max(1, Math.round(Math.pow(10, lg)));
      var x = toX(n);
      line.setAttribute("x1", x); line.setAttribute("x2", x); line.style.display = "";
      var rows = ["<strong>" + n + " run" + (n === 1 ? "" : "s") + "</strong>"];
      spec.series.forEach(function (s, i) {
        var v = 1 - Math.pow(1 - s.p, n);
        dots[i].setAttribute("cx", x); dots[i].setAttribute("cy", toY(v)); dots[i].style.display = "";
        rows.push('<span class="sw" style="background:var(' + s.color + ')"></span>' + s.label + ": " + (v * 100).toFixed(v < 0.995 ? 0 : 1) + "%");
      });
      tip.innerHTML = rows.join("<br>");
      tip.hidden = false;
      var box = wrap.getBoundingClientRect();
      var left = ev.clientX - box.left + 14;
      if (left > box.width - 190) left = ev.clientX - box.left - 190;
      tip.style.left = left + "px";
      tip.style.top = Math.max(0, ev.clientY - box.top - 20) + "px";
    }
    function hide() {
      tip.hidden = true; line.style.display = "none";
      dots.forEach(function (d) { d.style.display = "none"; });
    }
    svg.addEventListener("pointermove", move);
    svg.addEventListener("pointerleave", hide);
  });
})();
