import express from 'express';
import cors from 'cors';
import dotenv from 'dotenv';
import nodemailer from 'nodemailer';
import crypto from 'crypto';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
dotenv.config({ path: path.join(__dirname, '.env') });

const app = express();
const PORT = process.env.PORT || 8000;

app.use(cors());
app.use(express.json());

// ─── HMAC Secret (survives server restarts — stored in .env) ─────────────────
const TOKEN_SECRET = process.env.TOKEN_SECRET || 'phantom-phoenix-secret-key-2024';
const TOKEN_EXPIRY_MS = 60 * 60 * 1000; // 1 hour

// Log SMTP config at startup
const smtpUser = process.env.SMTP_USER || '(not set)';
const smtpPass = process.env.SMTP_PASS || '';
console.log(`[SMTP] User: ${smtpUser}`);
console.log(`[SMTP] Pass loaded: ${smtpPass.length > 0 ? `Yes (${smtpPass.length} chars)` : 'NO — check .env'}`);

// ─── Nodemailer transporter ───────────────────────────────────────────────────
const transporter = nodemailer.createTransport({
  host: process.env.SMTP_HOST || 'smtp.gmail.com',
  port: parseInt(process.env.SMTP_PORT || '587'),
  secure: process.env.SMTP_SECURE === 'true',
  auth: {
    user: process.env.SMTP_USER,
    pass: process.env.SMTP_PASS,
  },
});

// ─── Token helpers (HMAC-signed, no server storage needed) ───────────────────
function createToken(email) {
  const payload = Buffer.from(JSON.stringify({ email, expiry: Date.now() + TOKEN_EXPIRY_MS })).toString('base64url');
  const sig = crypto.createHmac('sha256', TOKEN_SECRET).update(payload).digest('hex');
  return `${payload}.${sig}`;
}

function verifyToken(token) {
  try {
    const [payload, sig] = token.split('.');
    if (!payload || !sig) return { valid: false, reason: 'Malformed token' };

    const expectedSig = crypto.createHmac('sha256', TOKEN_SECRET).update(payload).digest('hex');
    if (sig !== expectedSig) return { valid: false, reason: 'Invalid token signature' };

    const { email, expiry } = JSON.parse(Buffer.from(payload, 'base64url').toString());
    if (Date.now() > expiry) return { valid: false, reason: 'Token has expired' };

    return { valid: true, email };
  } catch {
    return { valid: false, reason: 'Token decode error' };
  }
}

// ─── POST /api/v1/auth/forgot-password ───────────────────────────────────────
app.post('/api/v1/auth/forgot-password', async (req, res) => {
  const { email } = req.body;

  if (!email) {
    return res.status(400).json({ success: false, message: 'Email is required' });
  }

  const token = createToken(email);
  const appUrl = process.env.APP_URL || req.headers.origin || 'http://localhost:5173';
  const resetLink = `${appUrl}/reset-password?token=${token}`;
  const timestamp = new Date().toLocaleString('en-IN', { timeZone: 'Asia/Kolkata' });

  console.log(`[Reset] Token created for ${email} (valid 1 hour)`);
  console.log(`[Reset] Link: ${resetLink}`);

  const mailOptions = {
    from: `"Phantom Phoenix" <${process.env.FROM_EMAIL || process.env.SMTP_USER}>`,
    to: email,
    replyTo: process.env.FROM_EMAIL || process.env.SMTP_USER,
    subject: 'Phantom Phoenix – Reset Your Password',
    headers: { 'X-Mailer': 'Phantom Phoenix Mailer v1.0' },
    html: `
      <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e2e8f0; border-radius: 8px; background-color: #ffffff;">
        <div style="text-align: center; margin-bottom: 20px;">
          <h2 style="color: #0ea5e9; margin: 0;">PHANTOM PHOENIX</h2>
          <p style="color: #64748b; font-size: 14px; margin: 5px 0 0 0;">Digital Media Authenticity &amp; AI Forensic Platform</p>
        </div>
        <hr style="border: 0; border-top: 1px solid #e2e8f0; margin-bottom: 20px;" />
        <p style="color: #334155; font-size: 16px; line-height: 1.5;">Hello,</p>
        <p style="color: #334155; font-size: 16px; line-height: 1.5;">
          We received a request to reset the password for the Phantom Phoenix account associated with
          <strong>${email}</strong>.
        </p>
        <p style="color: #334155; font-size: 16px; line-height: 1.5;">
          Click the button below to set a new password. This link is valid for <strong>1 hour</strong>.
        </p>
        <div style="text-align: center; margin: 30px 0;">
          <a href="${resetLink}"
             style="background-color: #0ea5e9; color: #ffffff; padding: 14px 32px; text-decoration: none;
                    border-radius: 8px; font-weight: bold; font-size: 16px; display: inline-block;">
            Set New Password
          </a>
        </div>
        <p style="color: #94a3b8; font-size: 13px;">If you didn't request a password reset, you can safely ignore this email.</p>
        <hr style="border: 0; border-top: 1px solid #e2e8f0; margin: 20px 0;" />
        <p style="color: #94a3b8; font-size: 11px; text-align: center; margin: 0;">
          This is an automated message from Phantom Phoenix. Do not reply to this email.
        </p>
      </div>
    `,
    text: `Phantom Phoenix – Reset Your Password\n\nWe received a request to reset the password for ${email}.\n\nPlease open the email on your device and click the "Set New Password" button.\n\nIf you did not request this, ignore this email.`,
  };

  try {
    await transporter.sendMail(mailOptions);
    console.log(`[Reset] Email sent to: ${email}`);
    res.status(200).json({ success: true, message: 'Password reset link sent to your email.' });
  } catch (error) {
    console.error('[Reset] Error sending email:', error.message);
    res.status(500).json({ success: false, message: `Failed to send email: ${error.message}` });
  }
});

// ─── POST /api/v1/auth/reset-password ────────────────────────────────────────
// Verifies the HMAC token and returns the associated email
app.post('/api/v1/auth/reset-password', (req, res) => {
  const { token } = req.body;

  if (!token) {
    return res.status(400).json({ success: false, message: 'Token is required' });
  }

  const result = verifyToken(token);

  if (!result.valid) {
    console.log(`[Reset] Invalid token: ${result.reason}`);
    return res.status(400).json({ success: false, message: 'Invalid or expired reset link. Please request a new one.' });
  }

  console.log(`[Reset] Token verified for: ${result.email}`);
  res.status(200).json({ success: true, email: result.email });
});

// ─── Server ───────────────────────────────────────────────────────────────────
app.listen(PORT, '0.0.0.0', () => {
  console.log(`\nPhantom Phoenix Server running on:`);
  console.log(`  Local:   http://localhost:${PORT}`);
  console.log(`  Network: http://10.70.37.230:${PORT}  <-- use this on your phone\n`);
});
