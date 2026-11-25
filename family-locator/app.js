/* Family Locator — consent-based live location for family & friends.
 *
 * Privacy model:
 *  - Nobody appears on the map until THEY tap "Start sharing" on their own phone
 *    and allow the browser's location prompt.
 *  - A member is only visible to people who typed the exact same circle code.
 *  - Sharing stops the moment they tap "Stop", close the tab, or lose the page.
 *
 * Sync backends (auto-selected):
 *  - "firebase": real cross-phone sync, if you filled in firebase-config.js.
 *  - "local":    same-device / multi-tab demo via BroadcastChannel + localStorage,
 *                so you can try the whole flow before setting up a server.
 */
(function () {
  "use strict";

  // ---------- tiny helpers ----------
  var $ = function (id) { return document.getElementById(id); };
  var now = function () { return Date.now(); };
  var STALE_MS = 60 * 1000;      // a member is "offline" if no update in 60s
  var SEND_EVERY_MS = 5000;      // throttle position broadcasts
  var colorFor = function (id) {
    var h = 0; for (var i = 0; i < id.length; i++) h = (h * 31 + id.charCodeAt(i)) % 360;
    return "hsl(" + h + " 62% 45%)";
  };
  var ago = function (ts) {
    var s = Math.max(0, Math.round((now() - ts) / 1000));
    if (s < 10) return "just now";
    if (s < 60) return s + "s ago";
    var m = Math.round(s / 60);
    if (m < 60) return m + " min ago";
    return Math.round(m / 60) + "h ago";
  };

  // ---------- identity (per browser) ----------
  var myId;
  try {
    myId = localStorage.getItem("fl_id");
    if (!myId) { myId = (crypto.randomUUID ? crypto.randomUUID() : "u" + Math.random().toString(36).slice(2) + now()); localStorage.setItem("fl_id", myId); }
  } catch (e) { myId = "u" + Math.random().toString(36).slice(2) + now(); }

  // =====================================================================
  //  SYNC BACKENDS
  //  Each backend implements: join(circle), publish(member|null),
  //  onChange(cb) -> cb(membersMap), leave()
  // =====================================================================

  function LocalBackend() {
    var circle = null, chan = null, cb = null, members = {};
    var key = function () { return "fl_members_" + circle; };
    var load = function () { try { return JSON.parse(localStorage.getItem(key()) || "{}"); } catch (e) { return {}; } };
    var save = function (m) { try { localStorage.setItem(key(), JSON.stringify(m)); } catch (e) {} };
    var emit = function () { if (cb) cb(members); };
    return {
      mode: "local",
      join: function (c) {
        circle = c; members = load();
        try { chan = new BroadcastChannel("fl_" + circle); } catch (e) { chan = null; }
        if (chan) chan.onmessage = function (ev) {
          var m = ev.data && ev.data.member;
          if (!m) return;
          if (m._gone) delete members[m.id]; else members[m.id] = m;
          save(members); emit();
        };
        emit();
      },
      publish: function (member) {
        if (!circle) return;
        if (member === null) {
          delete members[myId];
          if (chan) chan.postMessage({ member: { id: myId, _gone: true } });
        } else {
          members[member.id] = member;
          if (chan) chan.postMessage({ member: member });
        }
        save(members); emit();
      },
      onChange: function (fn) { cb = fn; },
      leave: function () { try { if (chan) chan.close(); } catch (e) {} }
    };
  }

  function FirebaseBackend(db) {
    var circle = null, ref = null, cb = null, sub = null;
    return {
      mode: "firebase",
      join: function (c) {
        circle = c; ref = db.ref("circles/" + c + "/members");
        sub = ref.on("value", function (snap) {
          var val = snap.val() || {};
          if (cb) cb(val);
        });
      },
      publish: function (member) {
        if (!ref) return;
        if (member === null) ref.child(myId).remove();
        else {
          var mref = ref.child(myId);
          mref.set(member);
          if (mref.onDisconnect) mref.onDisconnect().remove(); // auto-cleanup when tab dies
        }
      },
      onChange: function (fn) { cb = fn; },
      leave: function () { try { if (ref && sub) ref.off("value", sub); } catch (e) {} }
    };
  }

  function makeBackend() {
    // firebase-config.js may define window.FL_FIREBASE and load the SDK.
    if (window.firebase && window.FL_FIREBASE && window.FL_FIREBASE.databaseURL) {
      try {
        if (!firebase.apps.length) firebase.initializeApp(window.FL_FIREBASE);
        return FirebaseBackend(firebase.database());
      } catch (e) { console.warn("Firebase init failed, using local demo mode:", e); }
    }
    return LocalBackend();
  }

  var backend = makeBackend();

  // =====================================================================
  //  UI STATE
  // =====================================================================
  var map, markers = {}, myName = "", myCircle = "", sharing = false;
  var watchId = null, lastSent = 0, myPos = null, recenterOnNext = true;

  // ---------- onboarding ----------
  (function initOnboarding() {
    $("mode-note").textContent = backend.mode === "firebase"
      ? "Connected for live sharing across phones."
      : "Demo mode: syncs across tabs on this device. See README.md to enable real cross-phone sharing.";

    // prefill remembered name/circle
    try {
      $("name").value = localStorage.getItem("fl_name") || "";
      $("circle").value = localStorage.getItem("fl_circle") || "";
    } catch (e) {}

    $("make-code").addEventListener("click", function () {
      var words = ["falcon", "river", "acacia", "sunrise", "zebra", "copper", "baobab", "delta"];
      $("circle").value = words[Math.floor(Math.random() * words.length)] + "-" + Math.floor(1000 + Math.random() * 9000);
    });

    $("join-form").addEventListener("submit", function (e) {
      e.preventDefault();
      myName = $("name").value.trim().slice(0, 24);
      myCircle = $("circle").value.trim().toLowerCase().replace(/[^a-z0-9_-]/g, "").slice(0, 24);
      if (!myName || !myCircle) return;
      try { localStorage.setItem("fl_name", myName); localStorage.setItem("fl_circle", myCircle); } catch (e2) {}
      startApp();
    });
  })();

  // =====================================================================
  //  MAP APP
  // =====================================================================
  function startApp() {
    $("onboarding").hidden = true;
    $("app").hidden = false;
    $("circle-label").textContent = myCircle;

    map = L.map("map", { zoomControl: true, attributionControl: true }).setView([-15.4167, 28.2833], 12); // Lusaka default
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
      attribution: '&copy; OpenStreetMap contributors'
    }).addTo(map);

    backend.onChange(render);
    backend.join(myCircle);

    $("share-toggle").addEventListener("click", toggleShare);
    $("recenter").addEventListener("click", function () { recenterOnNext = true; if (myPos) map.setView([myPos.lat, myPos.lng], 15); });
    $("leave").addEventListener("click", leave);
    window.addEventListener("beforeunload", function () { if (sharing) backend.publish(null); });
  }

  function toggleShare() {
    if (sharing) { stopSharing(); return; }
    if (!("geolocation" in navigator)) {
      setStatus("This device has no location support.");
      return;
    }
    setStatus("Asking your device for permission…");
    watchId = navigator.geolocation.watchPosition(onPos, onPosError, {
      enableHighAccuracy: true, maximumAge: 10000, timeout: 20000
    });
    sharing = true;
    recenterOnNext = true;
    var btn = $("share-toggle");
    btn.textContent = "Stop sharing"; btn.classList.remove("off"); btn.classList.add("on");
  }

  function stopSharing() {
    sharing = false;
    if (watchId !== null) { navigator.geolocation.clearWatch(watchId); watchId = null; }
    backend.publish(null); // remove myself from everyone's map
    var btn = $("share-toggle");
    btn.textContent = "Start sharing"; btn.classList.remove("on"); btn.classList.add("off");
    setStatus("You stopped sharing. You're off the map.");
  }

  function onPos(p) {
    myPos = { lat: p.coords.latitude, lng: p.coords.longitude, acc: p.coords.accuracy };
    if (recenterOnNext) { map.setView([myPos.lat, myPos.lng], 15); recenterOnNext = false; }
    var t = now();
    if (t - lastSent >= SEND_EVERY_MS) {
      lastSent = t;
      backend.publish({ id: myId, name: myName, lat: myPos.lat, lng: myPos.lng, acc: Math.round(myPos.acc || 0), t: t });
    }
    setStatus("Sharing live · accuracy ±" + Math.round(myPos.acc || 0) + "m");
  }

  function onPosError(err) {
    sharing = false;
    var btn = $("share-toggle");
    btn.textContent = "Start sharing"; btn.classList.remove("on"); btn.classList.add("off");
    if (err.code === 1) setStatus("Permission denied. Allow location in your browser to share.");
    else if (err.code === 2) setStatus("Couldn't get a location fix. Try moving to open sky.");
    else setStatus("Location timed out. Tap Start sharing to retry.");
  }

  // ---------- render roster + markers ----------
  function render(membersMap) {
    var list = Object.keys(membersMap).map(function (k) { return membersMap[k]; })
      .filter(function (m) { return m && typeof m.lat === "number"; });

    // markers
    var seen = {};
    list.forEach(function (m) {
      seen[m.id] = true;
      var stale = now() - m.t > STALE_MS;
      var isMe = m.id === myId;
      var color = isMe ? getComputedStyle(document.documentElement).getPropertyValue("--accent").trim() || "#2f7d5b" : colorFor(m.id);
      var html = '<div class="marker-pin" style="background:' + color + (stale ? ";opacity:.45" : "") + '"><span>' + initials(m.name) + '</span></div>';
      var icon = L.divIcon({ className: isMe ? "me-marker" : "peer-marker", html: html, iconSize: [26, 26], iconAnchor: [13, 24], popupAnchor: [0, -22] });
      if (markers[m.id]) {
        markers[m.id].setLatLng([m.lat, m.lng]).setIcon(icon);
      } else {
        markers[m.id] = L.marker([m.lat, m.lng], { icon: icon }).addTo(map);
      }
      markers[m.id].bindPopup("<b>" + escapeHtml(m.name) + (isMe ? " (you)" : "") + "</b><br>" +
        (stale ? "last seen " + ago(m.t) : "live · " + ago(m.t)) + "<br>±" + (m.acc || 0) + "m");
    });
    // drop markers for people who left
    Object.keys(markers).forEach(function (id) {
      if (!seen[id]) { map.removeLayer(markers[id]); delete markers[id]; }
    });

    // roster list
    var ul = $("members"); ul.innerHTML = "";
    list.sort(function (a, b) { return (a.name || "").localeCompare(b.name || ""); });
    list.forEach(function (m) {
      var stale = now() - m.t > STALE_MS;
      var isMe = m.id === myId;
      var li = document.createElement("li");
      var color = isMe ? (getComputedStyle(document.documentElement).getPropertyValue("--accent").trim() || "#2f7d5b") : colorFor(m.id);
      li.innerHTML =
        '<span class="dot" style="background:' + color + (stale ? ";opacity:.4" : "") + '"></span>' +
        '<span class="who"><b>' + escapeHtml(m.name) + (isMe ? " (you)" : "") + '</b>' +
        '<small>' + (stale ? "offline · " + ago(m.t) : "live · " + ago(m.t)) + '</small></span>';
      li.addEventListener("click", function () { map.setView([m.lat, m.lng], 16); if (markers[m.id]) markers[m.id].openPopup(); });
      ul.appendChild(li);
    });
    $("roster-count").textContent = list.length + (list.length === 1 ? " person" : " people");
  }

  function leave() {
    if (sharing) backend.publish(null);
    backend.leave();
    location.reload();
  }

  // ---------- utils ----------
  function initials(name) {
    var parts = (name || "?").trim().split(/\s+/);
    return ((parts[0][0] || "?") + (parts[1] ? parts[1][0] : "")).toUpperCase();
  }
  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  function setStatus(msg) { $("status-line").textContent = msg; }

  // keep "x min ago" fresh
  setInterval(function () {
    if (!$("app").hidden) backend.onChange && render(lastMembers());
  }, 15000);
  var _last = {};
  var _origOnChange = backend.onChange;
  backend.onChange = function (fn) { _origOnChange(function (m) { _last = m; fn(m); }); };
  function lastMembers() { return _last; }
})();
