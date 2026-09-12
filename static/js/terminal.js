(function () {
  var input = document.getElementById("term-input");
  var output = document.getElementById("term-output");
  if (!input || !output) return;

  var postsEl = document.getElementById("term-posts");
  var posts = [];
  try {
    posts = JSON.parse(postsEl.textContent);
  } catch (e) {
    posts = [];
  }

  var baseURL = document.querySelector('.terminal-logo a.no-style').getAttribute("href");
  var history = [];
  var historyIndex = -1;

  function print(line) {
    output.textContent = line;
  }

  function run(raw) {
    var line = raw.trim();
    output.textContent = "";
    if (!line) return;

    var parts = line.split(/\s+/);
    var cmd = parts[0];
    var arg = parts.slice(1).join(" ");

    switch (cmd) {
      case "help":
        print("commands: ls, cd <dir>, cat <post>, clear, help");
        break;
      case "clear":
        output.textContent = "";
        break;
      case "ls":
        if (!posts.length) {
          print("blog/");
        } else {
          print(posts.map(function (p) { return p.slug; }).join("  "));
        }
        break;
      case "cd":
        if (!arg || arg === ".." || arg === "/" || arg === "~") {
          window.location.href = baseURL;
        } else if (arg.replace(/\/$/, "") === "blog") {
          window.location.href = baseURL + "blog/";
        } else {
          print("cd: no such directory: " + arg);
        }
        break;
      case "cat":
        if (!arg) {
          print("usage: cat <post>");
          break;
        }
        var needle = arg.replace(/\.md$/, "").toLowerCase();
        var match = posts.find(function (p) {
          return p.slug.toLowerCase() === needle;
        });
        if (match) {
          window.location.href = match.url;
        } else {
          print("cat: no such file: " + arg);
        }
        break;
      default:
        print(cmd + ": command not found (try 'help')");
    }
  }

  function resize() {
    input.style.width = input.value.length + "ch";
  }

  input.addEventListener("input", resize);

  input.addEventListener("keydown", function (e) {
    if (e.key === "Enter") {
      var value = input.value;
      input.value = "";
      resize();
      history.push(value);
      historyIndex = history.length;
      run(value);
    } else if (e.key === "ArrowUp") {
      if (historyIndex > 0) {
        historyIndex -= 1;
        input.value = history[historyIndex] || "";
        resize();
      }
      e.preventDefault();
    } else if (e.key === "ArrowDown") {
      if (historyIndex < history.length) {
        historyIndex += 1;
        input.value = history[historyIndex] || "";
        resize();
      }
      e.preventDefault();
    }
  });

  resize();
  input.focus();

  var prompt = document.querySelector(".terminal-prompt");
  if (prompt) {
    prompt.addEventListener("click", function (e) {
      if (e.target.closest("a, button")) return;
      input.focus();
    });
  }
})();
