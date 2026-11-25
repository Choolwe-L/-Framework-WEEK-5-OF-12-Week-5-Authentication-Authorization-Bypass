/* OPTIONAL — real cross-phone sync.
 *
 * Without this, the app runs in "demo mode" (syncs across tabs on one device),
 * which is perfect for trying it out. To let family members on DIFFERENT phones
 * see each other, set up a free Firebase Realtime Database and fill this in.
 *
 * Steps (5 minutes, free):
 *   1. Go to https://console.firebase.google.com  ->  Add project.
 *   2. Build -> Realtime Database -> Create database -> Start in "test mode"
 *      (fine for family use; lock it down later with the rules in README.md).
 *   3. Project settings -> General -> "Your apps" -> Web app -> copy the config.
 *   4. Paste the values below and uncomment the two <script> loader lines.
 *
 * Then add these two lines ABOVE this file in index.html (already commented there):
 *   <script src="https://www.gstatic.com/firebasejs/10.12.2/firebase-app-compat.js"></script>
 *   <script src="https://www.gstatic.com/firebasejs/10.12.2/firebase-database-compat.js"></script>
 */

// window.FL_FIREBASE = {
//   apiKey: "PASTE",
//   authDomain: "PASTE.firebaseapp.com",
//   databaseURL: "https://PASTE-default-rtdb.firebaseio.com",
//   projectId: "PASTE",
//   appId: "PASTE"
// };
