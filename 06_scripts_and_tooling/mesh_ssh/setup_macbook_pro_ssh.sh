#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Lauburu Mesh — MacBook Pro SSH Setup Script
# Run this script ON the MacBook Pro to authorize Mac Mini key access
# ─────────────────────────────────────────────────────────────────────────────

echo "🔐 Setting up SSH key authorization for Mac Mini → MacBook Pro..."

# Create .ssh dir if missing
mkdir -p ~/.ssh
chmod 700 ~/.ssh

# Install Mac Mini public keys into authorized_keys
cat >> ~/.ssh/authorized_keys << 'KEYS'
# Mac Mini M4 Pro (aaron@Aarons-Mac-mini.local) — ed25519
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIHBCVTl2xI3jRLUFvbasxL8BAao8waCSO8rE1Z5cl9lp aaron@Aarons-Mac-mini.local
# Mac Mini M4 Pro — rsa fallback
ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQDvB3Y52dG5QFSnAGf14j3koametoDXuWGteogpIqvXFoJ7KDmx7odnLFEBPVYxxUqMRSiNqAtgeSHPzJR2BOZC0N5qqY5C2E2CLs1OerYghMxX+rtCuxdyslLBx0YsIpPkA1LeZGGhzjNQMVsaAv8pOzLnENVaBT8cO4bXUPFftOJE9cNN4fWBjm2RMRVgjhrpOjo4MdzIjVxPpzUsHc6E1vnraAfCV3QHZfA7KoSbkPMiAfndabOma7kZUlhTQgUHL6HVHGg4tNSjQTioUdSao21zjCSHAduvfvWPiEo13Ulv8sd2b+NzTZ9AkQlUVnrMerkaJjei+dT/1cu8wrYhpn2RjDPG+xLAzCSFGvG5PMMA79AuSQHIvXUmFSXSzix+sjZkeZ/MdBJ+EGUhnftMRD6B8uG8NEs0cxQqlXXJzTd9tUIhpJptdAdHKP5+VqWtfJ6RQhgiJQb3QNzkqAecFtNf5xxvlx6xDRXam9NyyYTuK3xBOZqYg0dViykCbmM= aaronmaher@mac-2.local
KEYS

chmod 600 ~/.ssh/authorized_keys
echo "✅ authorized_keys updated"

# Enable SSH (Remote Login) on macOS if not already enabled
sudo systemsetup -setremotelogin on 2>/dev/null && echo "✅ Remote Login (SSH) enabled" || echo "ℹ️  Remote Login may already be enabled"

# Create the cold model vault directory
mkdir -p ~/model_vault_gguf_cold
echo "✅ Cold model vault created: ~/model_vault_gguf_cold"

echo ""
echo "🎉 Setup complete! Test from Mac Mini with:"
echo "   ssh aaronmaher@100.103.212.21"
echo "   or via TB4: ssh aaronmaher@169.254.187.138"
