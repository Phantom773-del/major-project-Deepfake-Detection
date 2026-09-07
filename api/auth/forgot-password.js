import nodemailer from 'nodemailer';
import crypto from 'crypto';

const TOKEN_SECRET = process.env.TOKEN_SECRET || 'phantom-phoenix-secret-key-2024';
const TOKEN_EXPIRY_MS = 60 * 60 * 1000; // 1 hour

function createToken(email) {
  const payload = Buffer.from(JSON.stringify({ email, expiry: Date.now() + TOKEN_EXPIRY_MS })).toString('base64url');
  const sig = crypto.createHmac('sha256', TOKEN_SECRET).update(payload).digest('hex');
  return `${payload}.${sig}`;
}

export default async function handler(req, res) {
  // Allow CORS
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');

  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  if (req.method !== 'POST') {
    return res.status(405).json({ success: false, message: 'Method not allowed' });
  }

  const { email } = req.body;

  if (!email) {
    return res.status(400).json({ success: false, message: 'Email is required' });
  }

  const token = createToken(email);
  const appUrl = process.env.APP_URL || `https://${req.headers.host}`;
  const resetLink = `${appUrl}/reset-password?token=${token}`;

  console.log(`[Reset] Token created for ${email} (valid 1 hour)`);
  console.log(`[Reset] Link: ${resetLink}`);

  const transporter = nodemailer.createTransport({
    host: process.env.SMTP_HOST || 'smtp.gmail.com',
    port: parseInt(process.env.SMTP_PORT || '587'),
    secure: process.env.SMTP_SECURE === 'true',
    auth: {
      user: process.env.SMTP_USER,
      pass: process.env.SMTP_PASS,
    },
  });

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
    return res.status(200).json({ success: true, message: 'Password reset link sent to your email.' });
  } catch (error) {
    console.error('[Reset] Error sending email:', error.message);
    return res.status(500).json({ success: false, message: `Failed to send email: ${error.message}` });
  }
}
