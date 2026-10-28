const crypto = require('crypto');

function hash() {
    // Weak crypto
    return crypto.createHash('sha256').update('test').digest('hex');
}
