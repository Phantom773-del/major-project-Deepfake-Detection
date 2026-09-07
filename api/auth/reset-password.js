import crypto from 'crypto';

const TOKEN_SECRET = process.env.TOKEN_SECRET || 'phantom-phoenix-secret-key-2024';

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

export default function handler(req, res) {
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
  return res.status(200).json({ success: true, email: result.email });
}
