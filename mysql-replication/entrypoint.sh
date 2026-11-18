#!/bin/bash
# MySQL tá»« chá»‘i Ä‘á»c file cáº¥u hÃ¬nh cÃ³ quyá»n world-writable. File mount tá»« Windows
# luÃ´n lÃ  777, nÃªn pháº£i háº¡ quyá»n trÆ°á»›c khi mysqld Ä‘á»c config.
set -e

for f in /etc/mysql/conf.d/*.cnf; do
  [ -e "$f" ] || continue
  chmod 644 "$f"
done

exec /usr/local/bin/docker-entrypoint.sh "$@"
