"""
Automated Instagram Long-Lived Access Token refresher.
Refreshes Instagram Graph API Long-Lived User Access Token before its 60-day expiry,
and optionally updates GitHub repository secret IG_ACCESS_TOKEN using GH_PAT.
"""
import os
import sys
import json
import base64
import urllib.request
import urllib.parse

def refresh_instagram_token(current_token):
    """
    Calls Meta Instagram Graph API refresh endpoint to extend long-lived token by 60 days.
    """
    url = "https://graph.instagram.com/refresh_access_token"
    params = urllib.parse.urlencode({
        "grant_type": "ig_refresh_token",
        "access_token": current_token
    })
    req = urllib.request.Request(f"{url}?{params}", headers={"User-Agent": "InstaAutoPoster/2.0"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            new_token = data.get("access_token")
            expires_in = data.get("expires_in", 0)
            days = expires_in // 86400
            print(f"Token refresh successful! New token validity: {days} days ({expires_in} seconds).")
            return new_token
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", errors="replace")
        print(f"::error::Instagram Token Refresh Failed: {err}")
        sys.exit(1)
    except Exception as e:
        print(f"::error::Network error while refreshing token: {e}")
        sys.exit(1)

def update_github_secret(new_token, repo, gh_pat):
    """
    Encrypts new_token with repository public key and updates IG_ACCESS_TOKEN secret on GitHub.
    """
    try:
        from nacl import encoding, public
    except ImportError:
        print("::warning::PyNaCl library not installed. Cannot encrypt and update GitHub secret automatically.")
        return False

    headers = {
        "Authorization": f"Bearer {gh_pat}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "InstaAutoPoster-SecretUpdater"
    }

    # 1. Get repository public key
    pubkey_url = f"https://api.github.com/repos/{repo}/actions/secrets/public-key"
    req = urllib.request.Request(pubkey_url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            key_data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"::warning::Failed to fetch GitHub repository public key: {e}")
        return False

    key_id = key_data["key_id"]
    public_key_b64 = key_data["key"]

    # 2. Encrypt token using libsodium sealed box
    public_key = public.PublicKey(public_key_b64.encode("utf-8"), encoding.Base64Encoder)
    sealed_box = public.SealedBox(public_key)
    encrypted = sealed_box.encrypt(new_token.encode("utf-8"))
    encrypted_b64 = base64.b64encode(encrypted).decode("utf-8")

    # 3. Update secret
    secret_url = f"https://api.github.com/repos/{repo}/actions/secrets/IG_ACCESS_TOKEN"
    payload = json.dumps({
        "encrypted_value": encrypted_b64,
        "key_id": key_id
    }).encode("utf-8")
    
    put_req = urllib.request.Request(secret_url, data=payload, method="PUT", headers=headers)
    try:
        with urllib.request.urlopen(put_req, timeout=30) as resp:
            if resp.status in (201, 204):
                print("Successfully updated IG_ACCESS_TOKEN secret in GitHub repository!")
                return True
    except Exception as e:
        print(f"::warning::Failed to update GitHub secret via API: {e}")
        return False

    return False

def main():
    current_token = os.environ.get("IG_ACCESS_TOKEN", "").strip()
    if not current_token:
        print("::error::IG_ACCESS_TOKEN is not provided in environment.")
        sys.exit(1)

    print("Refreshing Instagram Long-Lived Access Token...")
    new_token = refresh_instagram_token(current_token)

    repo = os.environ.get("GITHUB_REPOSITORY", "Sabirusmani077/insta-autoposter")
    gh_pat = os.environ.get("GH_PAT", "").strip()

    if gh_pat:
        print("GH_PAT found. Attempting automatic GitHub repository secret update...")
        updated = update_github_secret(new_token, repo, gh_pat)
        if not updated:
            print("::warning::Could not automatically update GitHub secret via GH_PAT.")
    else:
        print("GH_PAT secret not provided. The token was refreshed on Meta's servers, but GitHub secret was not updated automatically.")
        print("To enable full auto-refresh of repository secrets, add a Personal Access Token named GH_PAT.")

if __name__ == "__main__":
    main()
