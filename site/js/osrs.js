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
    t.addEventListener("click", function (ev) {
      if (t.tagName === "A") ev.preventDefault();
      showTab(t.getAttribute("data-tab"));
    });
  });
  // Restore the panel the reader last chose; otherwise the Quest List.
  var savedTab = load("sessionStorage", "vtb.tab", null);
  showTab(savedTab && $('[data-panel="' + savedTab + '"]') ? savedTab : "quests");

  // Don't leave a focus highlight on side-panel buttons after a mouse click.
  document.addEventListener("click", function (ev) {
    var t = ev.target.closest && ev.target.closest(".sidepanel a, .sidepanel button");
    if (t && ev.detail > 0) t.blur();
  });

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
    if (a.hasAttribute("data-tab")) return ["Open", a.getAttribute("title") || "", "target"];
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
          { label: item.getAttribute("data-verb"), target: name, run: function () { item.click(); } },
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
        { label: "Read", target: p.title, run: function () { a.click(); } },
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
  var world = $("#world");
  var article = null;

  function updateRun() {
    if (!runVal) return;
    if (!article) { runVal.textContent = 100; return; }
    var rect = article.getBoundingClientRect();
    var viewH = window.innerHeight;
    var total = rect.height - viewH * 0.6;
    var done = Math.min(1, Math.max(0, (viewH * 0.4 - rect.top) / Math.max(1, total)));
    runVal.textContent = Math.round(100 - done * 100);
  }
  if (world) world.addEventListener("scroll", updateRun, { passive: true });
  window.addEventListener("scroll", updateRun, { passive: true });
  window.addEventListener("resize", updateRun);

  /* ---------------------------------------------------------- quest complete */

  var dialog = $("#quest-complete");
  var lastFocus = null;
  var io = null;
  var ioTimer = null;

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

  /* ---------------------------------------------------------- per-page setup */

  function initPage() {
    current = document.body.getAttribute("data-slug") || "";
    paintQuests();

    // Highlight the inventory item for the current page.
    $$(".item").forEach(function (a) {
      if (a.getAttribute("href") === window.location.pathname) a.setAttribute("aria-current", "page");
      else a.removeAttribute("aria-current");
    });

    // Keep the current quest in view in the quest list.
    var currentLink = current && $('.quest-list [data-quest="' + current + '"]');
    var body = $(".tab-body");
    if (currentLink && body && !currentLink.closest("[hidden]")) {
      body.scrollTop = currentLink.offsetTop - body.clientHeight / 2;
    }

    article = $(".post .prose");
    updateRun();

    // Award the quest when the reader reaches the end of the post.
    if (io) { io.disconnect(); io = null; }
    clearTimeout(ioTimer);
    var end = $("#quest-end");
    var slug = current;
    if (end && slug && bySlug[slug] && !completed[slug] && "IntersectionObserver" in window) {
      io = new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting && slug === current) {
            io.disconnect();
            completeQuest(bySlug[slug]);
          }
        });
      }, { threshold: 1 });
      // Wait a moment so a quick jump to the bottom of the page doesn't count.
      var observer = io;
      ioTimer = setTimeout(function () { observer.observe(end); }, 4000);
    }
  }
  initPage();

  /* ---------------------------------------------------------- in-place navigation */
  // Clicking a link on this site swaps the scroll's contents instead of reloading
  // the whole page, so the side panel stays put. Falls back to a normal page load.

  var navToken = 0;

  function sameSitePage(url) {
    if (url.origin !== window.location.origin) return false;
    var last = url.pathname.split("/").pop();
    return last === "" || /\.html?$/.test(last);
  }

  function swapIn(doc, url) {
    var next = doc.getElementById("world");
    if (!next || !world) return false;
    world.innerHTML = next.innerHTML;
    document.title = doc.title;
    document.body.setAttribute("data-slug", doc.body.getAttribute("data-slug") || "");
    // Scripts added through innerHTML don't run; re-create them (the comments widget).
    $$("script", world).forEach(function (old) {
      var s = document.createElement("script");
      Array.prototype.forEach.call(old.attributes, function (at) { s.setAttribute(at.name, at.value); });
      s.text = old.text;
      old.parentNode.replaceChild(s, old);
    });
    return true;
  }

  function scrollToTarget(hash) {
    var target = hash && document.getElementById(decodeURIComponent(hash.slice(1)));
    if (target) { target.scrollIntoView(); return; }
    if (world) world.scrollTop = 0;
    window.scrollTo(0, 0);
  }

  function navigate(href, push) {
    var url = new URL(href, window.location.href);
    var token = ++navToken;
    closeMenu();
    fetch(url.pathname + url.search, { credentials: "same-origin" })
      .then(function (r) {
        if (!r.ok) throw new Error("status " + r.status);
        return r.text();
      })
      .then(function (html) {
        if (token !== navToken) return;
        var doc = new DOMParser().parseFromString(html, "text/html");
        if (push) window.history.pushState({}, "", url.href);
        if (!swapIn(doc, url)) throw new Error("no content");
        initPage();
        scrollToTarget(url.hash);
      })
      .catch(function () {
        if (token === navToken) window.location.href = url.href;
      });
  }

  if (window.history && window.history.pushState && window.fetch && window.DOMParser && world) {
    document.addEventListener("click", function (ev) {
      if (ev.defaultPrevented || ev.button !== 0 || ev.metaKey || ev.ctrlKey || ev.shiftKey || ev.altKey) return;
      var a = ev.target.closest && ev.target.closest("a[href]");
      if (!a || a.target === "_blank" || a.hasAttribute("download")) return;
      var url = new URL(a.href, window.location.href);
      if (!sameSitePage(url)) return;
      if (url.pathname === window.location.pathname && url.search === window.location.search) {
        if (url.hash) return;             // in-page anchor: let the browser handle it
        ev.preventDefault();
        scrollToTarget("");               // link to the page we're already on: just go to the top
        return;
      }
      ev.preventDefault();
      navigate(url.href, true);
    });
    window.addEventListener("popstate", function () { navigate(window.location.href, false); });
  }
})();
