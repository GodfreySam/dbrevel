#!/bin/bash
# Run this script after extracting the dbrevel archive
# It makes all shell scripts executable

echo "Making scripts executable..."

chmod +x setup.sh
chmod +x test_api.sh
chmod +x backend/startup.sh

echo "✅ Done! Scripts are now executable."
echo ""
echo "You can now run:"
echo "  ./setup.sh"
echo "  ./test_api.sh"
echo "  cd backend && ./startup.sh"
