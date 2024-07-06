from ecdsa import SigningKey, SECP256k1

def generate_user(private_key=None): 
    if not private_key: 
        private_key = SigningKey.generate(curve=SECP256k1).to_string().hex()
    public_key = get_public_key(private_key)
    user = {"public_key": public_key, "id": f"user:{public_key}"}
    return user, private_key

def get_public_key(private_key_hex):
    private_key = SigningKey.from_string(bytes.fromhex(private_key_hex), curve=SECP256k1)
    public_key = private_key.get_verifying_key()
    return public_key.to_string().hex()