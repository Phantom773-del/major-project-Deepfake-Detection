import nodemailer from "nodemailer";
import dotenv from "dotenv";
import { fileURLToPath } from "url";
import path from "path";
const __dirname = path.dirname(fileURLToPath(import.meta.url));
dotenv.config({ path: path.join(__dirname, ".env") });
const user = process.env.SMTP_USER;
const pass = process.env.SMTP_PASS;
console.log("User:", user, "| Pass chars:", pass?.length ?? 0);
const t = nodemailer.createTransport({ host:"smtp.gmail.com", port:587, secure:false, auth:{user,pass} });
t.verify()
  .then(() => { console.log("VERIFY OK - connection works"); return t.sendMail({ from:user, to:user, subject:"Phantom Phoenix SMTP Test", text:"SMTP is working! Password reset emails will now deliver." }); })
  .then(info => { console.log("SENT OK:", info.messageId, info.response); })
  .catch(err => { console.log("ERROR", err.code, err.message); if(err.response) console.log("Gmail:", err.response); });
