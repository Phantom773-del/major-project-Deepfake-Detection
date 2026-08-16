import { initializeApp } from 'firebase/app';
import { getAuth, GoogleAuthProvider, GithubAuthProvider } from 'firebase/auth';

const firebaseConfig = {
  apiKey: "AIzaSyBe3OnbcWX346nqkhQJgpFpxAkF2ibRqig",
  authDomain: "phantom-566ce.firebaseapp.com",
  projectId: "phantom-566ce",
  storageBucket: "phantom-566ce.firebasestorage.app",
  messagingSenderId: "3363946074",
  appId: "1:3363946074:web:426b94af5d0a5030572263",
  measurementId: "G-2J2KL79TPB"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);

// Initialize Firebase Authentication and get a reference to the service
export const auth = getAuth(app);

// Initialize Auth Providers
export const googleProvider = new GoogleAuthProvider();
export const githubProvider = new GithubAuthProvider();
