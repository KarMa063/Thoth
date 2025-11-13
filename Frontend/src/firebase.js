import { initializeApp } from "firebase/app";
import {
  getAuth,
  GoogleAuthProvider,
  signInWithPopup,
  signOut,
  onAuthStateChanged,
  createUserWithEmailAndPassword,
  signInWithEmailAndPassword,
  updateProfile,
} from "firebase/auth";
// (Optional) If you want to save extra user data:
import { getFirestore, doc, setDoc, serverTimestamp } from "firebase/firestore";

const cfg = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
  appId: import.meta.env.VITE_FIREBASE_APP_ID,
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID,
};

const app = initializeApp(cfg);
export const auth = getAuth(app);
const provider = new GoogleAuthProvider();

// ----- Google -----
export async function googleLogin() {
  const res = await signInWithPopup(auth, provider);
  return res.user;
}
export async function googleLogout() {
  await signOut(auth);
}
export function observeAuth(cb) {
  return onAuthStateChanged(auth, cb);
}

// ----- Email/Password (Traditional) -----
export async function emailSignUp({ name, email, password }) {
  const cred = await createUserWithEmailAndPassword(auth, email, password);
  if (name) {
    await updateProfile(cred.user, { displayName: name });
  }
  // Optional: store a user document in Firestore
  try {
    const db = getFirestore(app);
    await setDoc(doc(db, "users", cred.user.uid), {
      name: name || cred.user.displayName || "",
      email: cred.user.email,
      provider: "password",
      createdAt: serverTimestamp(),
    }, { merge: true });
  } catch (_) {}
  return cred.user;
}

export async function emailSignIn({ email, password }) {
  const cred = await signInWithEmailAndPassword(auth, email, password);
  return cred.user;
}
