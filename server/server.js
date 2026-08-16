import express from 'express';
import cors from 'cors';
import dotenv from 'dotenv';
import nodemailer from 'nodemailer';

dotenv.config();

const app = express();
const PORT = process.env.PORT || 8000;

app.use(cors());
app.use(express.json());

app.post('/api/v1/auth/forgot-password', async (req, res) => {
  const { email } = req.body;

  if (!email) {
    return res.status(400).json({ success: false, message: 'Email is required' });
  }

  // Configure Transporter
  const transporter = nodemailer.createTransport({
    host: process.env.SMTP_HOST || 'smtp.gmail.com',
    port: parseInt(process.env.SMTP_PORT || '587'),
    secure: process.env.SMTP_SECURE === 'true' || false, // true for 465, false for other ports
    auth: {
      user: process.env.SMTP_USER,
      pass: process.env.SMTP_PASS,
    },
  });

  // Mail options
  const resetLink = `${req.headers.origin || 'http://localhost:5173'}/login?reset=success`;
  const mailOptions = {
    from: process.env.FROM_EMAIL || process.env.SMTP_USER,
    to: email,
    subject: 'Phantom Phoenix - Password Reset Link',
    html: `
      <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e2e8f0; border-radius: 8px; background-color: #ffffff;">
        <div style="text-align: center; margin-bottom: 20px;">
          <h2 style="color: #0ea5e9; margin: 0;">PHANTOM PHOENIX</h2>
          <p style="color: #64748b; font-size: 14px; margin: 5px 0 0 0;">Digital Media Authenticity & AI Forensic Platform</p>
        </div>
        <hr style="border: 0; border-top: 1px solid #e2e8f0; margin-bottom: 20px;" />
        <p style="color: #334155; font-size: 16px; line-height: 1.5;">Hello,</p>
        <p style="color: #334155; font-size: 16px; line-height: 1.5;">We received a request to reset the password for your Phantom Phoenix account. Click the button below to log back in and proceed:</p>
        <div style="text-align: center; margin: 30px 0;">
          <a href="${resetLink}" style="background-color: #0ea5e9; color: #ffffff; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold; font-size: 16px; display: inline-block;">Reset Password / Login</a>
        </div>
        <p style="color: #64748b; font-size: 14px; line-height: 1.5;">If you didn't request a password reset, you can safely ignore this email.</p>
        <hr style="border: 0; border-top: 1px solid #e2e8f0; margin: 20px 0;" />
        <p style="color: #94a3b8; font-size: 12px; text-align: center; margin: 0;">This is an automated message, please do not reply directly to this email.</p>
      </div>
    `,
  };

  try {
    if (!process.env.SMTP_USER || !process.env.SMTP_PASS || process.env.SMTP_USER === 'your_email@gmail.com' || process.env.SMTP_PASS === 'your_gmail_app_password') {
      console.warn('Real SMTP_USER or SMTP_PASS environment variables are not set. Logging email content to console instead of sending real email:');
      console.log('--- EMAIL MOCK START ---');
      console.log(`To: ${email}`);
      console.log(`Subject: ${mailOptions.subject}`);
      console.log(`Reset Link: ${resetLink}`);
      console.log('------------------------');
      return res.status(200).json({
        success: true,
        message: 'Mock email logged to server console (SMTP credentials missing).',
        isMock: true,
      });
    }

    await transporter.sendMail(mailOptions);
    console.log(`Password reset email successfully sent to: ${email}`);
    res.status(200).json({ success: true, message: 'Password reset link sent successfully.' });
  } catch (error) {
    console.error('Error sending password reset email:', error);
    res.status(500).json({ success: false, message: 'Failed to send password reset email. Please check server logs.' });
  }
});

app.listen(PORT, () => {
  console.log(`Phantom Phoenix Mock Server running on http://localhost:${PORT}`);
});
