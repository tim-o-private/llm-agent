#!/usr/bin/env bash
# Verify bwrap sandbox functionality.
# Exits 0 if all checks pass, 1 if any fail.

set -e

echo "=== Bwrap Sandbox Verification ==="

# Check bwrap binary exists
if ! command -v bwrap &>/dev/null; then
    echo "FAIL: bwrap binary not found"
    exit 1
fi
echo "PASS: bwrap binary found at $(which bwrap)"

# Create temp dirs for test
SYSTEM_DIR=$(mktemp -d)
USER_DIR=$(mktemp -d)
echo "test content" > "$SYSTEM_DIR/test.txt"
trap "rm -rf $SYSTEM_DIR $USER_DIR" EXIT

# Build common bwrap args
BWRAP_ARGS=(
    --unshare-all --die-with-parent
    --ro-bind "$SYSTEM_DIR" /system
    --bind "$USER_DIR" /user
    --ro-bind /usr /usr
    --ro-bind /bin /bin
    --ro-bind /lib /lib
    --tmpfs /tmp --dev /dev --proc /proc
    --chdir /user
)

# Conditionally add /lib64
if [ -d /lib64 ]; then
    BWRAP_ARGS+=(--ro-bind /lib64 /lib64)
fi

# Test 1: Basic namespace creation
OUTPUT=$(bwrap "${BWRAP_ARGS[@]}" -- echo "hello from sandbox" 2>&1)
if [ "$OUTPUT" = "hello from sandbox" ]; then
    echo "PASS: Basic namespace creation"
else
    echo "FAIL: Basic namespace creation: $OUTPUT"
    exit 1
fi

# Test 2: Read-only system mount
# Try writing to /system — should fail
RESULT=$(bwrap "${BWRAP_ARGS[@]}" \
    -- /bin/sh -c "echo fail > /system/test.txt 2>&1; echo \$?" 2>&1)
if echo "$RESULT" | grep -q "1\|Read-only\|Permission denied"; then
    echo "PASS: System mount is read-only"
else
    echo "FAIL: System mount should be read-only: $RESULT"
    exit 1
fi

# Test 3: Writable user mount
bwrap "${BWRAP_ARGS[@]}" \
    -- /bin/sh -c "echo 'written in sandbox' > /user/output.txt"
if [ -f "$USER_DIR/output.txt" ] && grep -q "written in sandbox" "$USER_DIR/output.txt"; then
    echo "PASS: User mount is writable"
else
    echo "FAIL: User mount should be writable"
    exit 1
fi

# Test 4: Python3 available
PYTHON_OUTPUT=$(bwrap "${BWRAP_ARGS[@]}" \
    -- python3 -c "print('python works')" 2>&1)
if [ "$PYTHON_OUTPUT" = "python works" ]; then
    echo "PASS: Python3 available in sandbox"
else
    echo "FAIL: Python3 not available: $PYTHON_OUTPUT"
    exit 1
fi

# Test 5: Host filesystem not visible
HOST_CHECK=$(bwrap "${BWRAP_ARGS[@]}" \
    -- /bin/sh -c "ls /home 2>/dev/null && echo 'visible' || echo 'hidden'" 2>&1)
if echo "$HOST_CHECK" | grep -q "hidden"; then
    echo "PASS: Host filesystem not visible"
else
    echo "FAIL: Host filesystem should not be visible: $HOST_CHECK"
    exit 1
fi

echo ""
echo "=== All checks passed ==="
