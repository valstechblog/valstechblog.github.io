/* valstechblog — interface behaviour. Plain JS, no dependencies. */
(function () {
  "use strict";

  var $ = function (sel, root) { return (root || document).querySelector(sel); };
  var $$ = function (sel, root) { return Array.prototype.slice.call((root || document).querySelectorAll(sel)); };

  var data = { posts: [] };
  try { data = JSON.parse($("#site-data").textContent); } catch (e) {}
  var posts = data.posts || [];
  var bySlug = {};
  posts.forEach(function (p) { bySlug[p.slug] = p; });
  var current = document.body.getAttribute("data-slug") || "";

  function load(store, key, fallback) {
    try { var v = window[store].getItem(key); return v ? JSON.parse(v) : fallback; } catch (e) { return fallback; }
  }
  function save(store, key, value) {
    try { window[store].setItem(key, JSON.stringify(value)); } catch (e) {}
  }

  /* ---------------------------------------------------------- quest status */

  var completed = load("localStorage", "vtb.completed", {});

  function questPoints() {
    return Object.keys(completed).filter(function (s) { return bySlug[s]; }).length;
  }

  function paintQuests() {
    $$("[data-quest]").forEach(function (a) {
      var s = a.getAttribute("data-quest");
      a.classList.remove("q-new", "q-prog", "q-done");
      a.classList.add(completed[s] ? "q-done" : s === current ? "q-prog" : "q-new");
    });
    var qp = questPoints();
    $$("[data-qp]").forEach(function (el) { el.textContent = qp; });
  }
  paintQuests();

  /* ---------------------------------------------------------- side panel tabs */

  var tabs = $$(".tabs [data-tab]");
  function showTab(name) {
    tabs.forEach(function (t) {
      var on = t.getAttribute("data-tab") === name;
      t.classList.toggle("active", on);
      t.setAttribute("aria-selected", on ? "true" : "false");
    });
    $$("[data-panel]").forEach(function (p) { p.hidden = p.getAttribute("data-panel") !== name; });
    save("sessionStorage", "vtb.tab", name);
  }
  tabs.forEach(function (t) {
    t.addEventListener("click", function () { showTab(t.getAttribute("data-tab")); });
  });
  // Pages that open a specific tab (e.g. inventory pages) keep it; elsewhere restore the last one used.
  var activeTab = $(".tabs [data-tab].active");
  var savedTab = load("sessionStorage", "vtb.tab", null);
  if (activeTab && activeTab.getAttribute("data-tab") !== "quests") {
    save("sessionStorage", "vtb.tab", activeTab.getAttribute("data-tab"));
  } else if (savedTab && $('[data-panel="' + savedTab + '"]')) {
    showTab(savedTab);
  }

  // Highlight the inventory item for the current page.
  $$(".item").forEach(function (a) {
    if (a.getAttribute("href") === window.location.pathname) a.setAttribute("aria-current", "page");
  });

  // Keep the current quest in view in the quest list.
  var currentLink = $('.quest-list [data-quest="' + current + '"]');
  if (currentLink && currentLink.scrollIntoView) {
    var body = $(".tab-body");
    if (body) body.scrollTop = currentLink.offsetTop - body.clientHeight / 2;
  }

  /* ---------------------------------------------------------- mouse-over text */

  var mouseover = $("#mouseover");
  var examineTimer = null;

  function setMouseover(action, target, cls) {
    if (!mouseover || examineTimer) return;
    mouseover.textContent = "";
    mouseover.appendChild(document.createTextNode(action));
    if (target) {
      mouseover.appendChild(document.createTextNode(" "));
      var span = document.createElement("span");
      span.className = cls || "target";
      span.textContent = target;
      mouseover.appendChild(span);
    }
  }

  function describeLink(a) {
    var quest = a.getAttribute("data-quest");
    if (quest && bySlug[quest]) return ["Read", bySlug[quest].title, "target"];
    if (a.hasAttribute("data-verb")) return [a.getAttribute("data-verb"), a.getAttribute("data-name") || "", "target"];
    var href = a.getAttribute("href") || "";
    if (/^https?:\/\//.test(href)) {
      var host = href.replace(/^https?:\/\/(www\.)?/, "").split("/")[0];
      return ["Visit", host, "ext"];
    }
    var label = (a.getAttribute("title") || a.textContent || "").trim().replace(/\s+/g, " ");
    return ["Go-to", label.slice(0, 60), "target"];
  }

  if (mouseover) {
    document.addEventListener("mouseover", function (ev) {
      var a = ev.target.closest && ev.target.closest("a, button");
      if (!a) { setMouseover("Walk here"); return; }
      if (a.tagName === "BUTTON") {
        setMouseover("Select", (a.getAttribute("title") || a.textContent || "").trim(), "target");
        return;
      }
      var d = describeLink(a);
      setMouseover(d[0], d[1], d[2]);
    });
  }

  function examine(text) {
    if (!mouseover) return;
    clearTimeout(examineTimer);
    examineTimer = null;
    mouseover.textContent = "";
    var span = document.createElement("span");
    span.className = "examine";
    span.textContent = text;
    mouseover.appendChild(span);
    examineTimer = setTimeout(function () { examineTimer = null; setMouseover("Walk here"); }, 4500);
  }

  /* ---------------------------------------------------------- right-click menu */

  var menu = $("#ctx-menu");

  function closeMenu() { if (menu) menu.hidden = true; }

  function openMenu(x, y, options) {
    menu.textContent = "";
    var head = document.createElement("p");
    head.className = "ctx-head";
    head.textContent = "Choose Option";
    menu.appendChild(head);
    options.forEach(function (opt) {
      var b = document.createElement("button");
      b.type = "button";
      b.setAttribute("role", "menuitem");
      b.appendChild(document.createTextNode(opt.label));
      if (opt.target) {
        b.appendChild(document.createTextNode(" "));
        var t = document.createElement("span");
        t.className = "target";
        t.textContent = opt.target;
        b.appendChild(t);
      }
      b.addEventListener("click", function () { closeMenu(); if (opt.run) opt.run(); });
      menu.appendChild(b);
    });
    menu.hidden = false;
    var w = menu.offsetWidth, h = menu.offsetHeight;
    menu.style.left = Math.max(4, Math.min(x - w / 2, window.innerWidth - w - 4)) + "px";
    menu.style.top = Math.max(4, Math.min(y - 8, window.innerHeight - h - 4)) + "px";
    var first = menu.querySelector("button");
    if (first) first.focus({ preventScroll: true });
  }

  if (menu) {
    document.addEventListener("contextmenu", function (ev) {
      var item = ev.target.closest && ev.target.closest("[data-item]");
      if (item) {
        ev.preventDefault();
        var name = item.getAttribute("data-name");
        openMenu(ev.clientX, ev.clientY, [
          { label: item.getAttribute("data-verb"), target: name, run: function () { window.location.href = item.getAttribute("href"); } },
          { label: "Examine", target: name, run: function () { examine(item.getAttribute("data-examine") || name); } },
          { label: "Cancel" }
        ]);
        return;
      }
      var a = ev.target.closest && ev.target.closest("[data-quest]");
      if (!a) return;
      var p = bySlug[a.getAttribute("data-quest")];
      if (!p) return;
      ev.preventDefault();
      var status = completed[p.slug] ? "You've completed this quest." : "You haven't completed this quest yet.";
      openMenu(ev.clientX, ev.clientY, [
        { label: "Read", target: p.title, run: function () { window.location.href = p.url; } },
        { label: "Examine", target: p.title, run: function () {
            examine("Published " + p.date + ". Length: " + p.length + " (" + p.words.toLocaleString() + " words). " + status);
          } },
        { label: "Cancel" }
      ]);
    });
    document.addEventListener("mousedown", function (ev) { if (!menu.hidden && !menu.contains(ev.target)) closeMenu(); });
    document.addEventListener("keydown", function (ev) { if (ev.key === "Escape") closeMenu(); });
    window.addEventListener("blur", closeMenu);
    var world = $("#world");
    if (world) world.addEventListener("scroll", closeMenu, { passive: true });
  }

  /* ---------------------------------------------------------- run energy (reading progress) */

  var runVal = $("#run-val");
  var article = $(".post .prose");
  var world = $("#world");

  function updateRun() {
    if (!runVal || !article) return;
    var rect = article.getBoundingClientRect();
    var viewH = window.innerHeight;
    var total = rect.height - viewH * 0.6;
    var done = Math.min(1, Math.max(0, (viewH * 0.4 - rect.top) / Math.max(1, total)));
    runVal.textContent = Math.round(100 - done * 100);
  }
  if (article) {
    (world || window).addEventListener("scroll", updateRun, { passive: true });
    window.addEventListener("scroll", updateRun, { passive: true });
    window.addEventListener("resize", updateRun);
    updateRun();
  }

  /* ---------------------------------------------------------- quest complete */

  var end = $("#quest-end");
  var dialog = $("#quest-complete");
  var lastFocus = null;

  function xpDrop(amount) {
    var box = $("#xp-drops");
    if (!box) return;
    var drop = document.createElement("div");
    drop.className = "xp-drop";
    var icon = $(".qc-icon .px");
    if (icon) drop.appendChild(icon.cloneNode(true));
    drop.appendChild(document.createTextNode("+" + amount.toLocaleString()));
    box.appendChild(drop);
    setTimeout(function () { drop.remove(); }, 2600);
  }

  function closeDialog() {
    dialog.hidden = true;
    if (lastFocus && lastFocus.focus) lastFocus.focus({ preventScroll: true });
  }

  function completeQuest(p) {
    completed[p.slug] = Date.now();
    save("localStorage", "vtb.completed", completed);
    paintQuests();
    xpDrop(p.words);
    if (!dialog) return;
    $("#qc-name").textContent = p.title;
    $("#qc-xp").textContent = p.words.toLocaleString();
    lastFocus = document.activeElement;
    dialog.hidden = false;
    $("#qc-close").focus({ preventScroll: true });
  }

  if (dialog) {
    $("#qc-close").addEventListener("click", closeDialog);
    dialog.addEventListener("click", function (ev) { if (ev.target === dialog) closeDialog(); });
    document.addEventListener("keydown", function (ev) { if (ev.key === "Escape" && !dialog.hidden) closeDialog(); });
  }

  if (end && current && bySlug[current] && !completed[current] && "IntersectionObserver" in window) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          io.disconnect();
          completeQuest(bySlug[current]);
        }
      });
    }, { threshold: 1 });
    // Wait a moment so a quick jump to the bottom of the page on load doesn't count.
    setTimeout(function () { io.observe(end); }, 4000);
  }
})();
