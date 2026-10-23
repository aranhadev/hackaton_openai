#!/bin/sh
set -eu

password="${EXAM_PASSWORD:-exam}"
printf 'exam:%s\n' "$password" | chpasswd

if [ -n "${EXAMSHELL_PUBLIC_GIT_URL:-}" ]; then
    printf '\nSetEnv EXAMSHELL_PUBLIC_GIT_URL=%s\n' "$EXAMSHELL_PUBLIC_GIT_URL" >> /etc/ssh/sshd_config
fi

mkdir -p /run/sshd /var/lib/examshell/git /var/lib/examshell/sessions
chown -R git:git /var/lib/examshell/git
chmod 2775 /var/lib/examshell/git
chown exam:exam /var/lib/examshell/sessions
chmod 0700 /var/lib/examshell/sessions

if [ ! -f /etc/ssh/ssh_host_ed25519_key ]; then
    ssh-keygen -q -t ed25519 -N '' -f /etc/ssh/ssh_host_ed25519_key
fi
if [ ! -f /etc/ssh/ssh_host_rsa_key ]; then
    ssh-keygen -q -t rsa -b 3072 -N '' -f /etc/ssh/ssh_host_rsa_key
fi

if [ ! -d /var/lib/examshell/git/exam.git ]; then
    git init --bare --initial-branch=master /var/lib/examshell/git/exam.git
    git init --initial-branch=master /tmp/exam-seed
    git -C /tmp/exam-seed config user.name 'ExamShell subjects'
    git -C /tmp/exam-seed config user.email 'examshell@localhost'
    mkdir -p /tmp/exam-seed/subjects /tmp/exam-seed/rendu
    cp -R /opt/examshell/subjects/ft_strlen /tmp/exam-seed/subjects/ft_strlen
    touch /tmp/exam-seed/rendu/.gitkeep
    git -C /tmp/exam-seed add subjects rendu
    git -C /tmp/exam-seed commit -m 'Initialize Rank 02 exam repository'
    git -C /tmp/exam-seed push /var/lib/examshell/git/exam.git master
    git --git-dir=/var/lib/examshell/git/exam.git config daemon.export true
    git --git-dir=/var/lib/examshell/git/exam.git config daemon.receivepack true
    git --git-dir=/var/lib/examshell/git/exam.git config receive.denyNonFastForwards true
    git --git-dir=/var/lib/examshell/git/exam.git config receive.denyDeletes true
    git --git-dir=/var/lib/examshell/git/exam.git config core.sharedRepository group
    chown -R git:git /var/lib/examshell/git/exam.git
    chmod -R g+rwX /var/lib/examshell/git/exam.git
    rm -rf /tmp/exam-seed
fi

# Upgrade persistent exam volumes created with the former subjects/subject and
# rendu/exam nesting. Preserve existing submissions while flattening both paths.
if [ ! -f /var/lib/examshell/layout-v2 ]; then
    git config --system --add safe.directory /var/lib/examshell/git/exam.git
    migration=/tmp/exam-layout-migration
    rm -rf "$migration"
    git clone /var/lib/examshell/git/exam.git "$migration"
    git -C "$migration" config user.name 'ExamShell layout migration'
    git -C "$migration" config user.email 'examshell@localhost'
    changed=0

    if [ -d "$migration/subjects/subject" ]; then
        for old_subject in "$migration"/subjects/subject/*; do
            [ -d "$old_subject" ] || continue
            slug=$(basename "$old_subject")
            new_subject="$migration/subjects/$slug"
            mkdir -p "$new_subject"
            if [ -f "$old_subject/README.md" ]; then
                mv "$old_subject/README.md" "$new_subject/subject.en.md"
                changed=1
            fi
            for item in "$old_subject"/*; do
                [ -e "$item" ] || continue
                mv "$item" "$new_subject/"
                changed=1
            done
        done
        rm -rf "$migration/subjects/subject"
        changed=1
    fi

    if [ -d "$migration/rendu/exam" ]; then
        for item in "$migration"/rendu/exam/* "$migration"/rendu/exam/.[!.]*; do
            [ -e "$item" ] || continue
            name=$(basename "$item")
            if [ -d "$item" ] && [ -d "$migration/rendu/$name" ]; then
                cp -a "$item"/. "$migration/rendu/$name"/
                rm -rf "$item"
            else
                mv "$item" "$migration/rendu/"
            fi
            changed=1
        done
        rm -rf "$migration/rendu/exam"
        changed=1
    fi

    if [ "$changed" -eq 1 ]; then
        git -C "$migration" add -A
        git -C "$migration" commit -m 'Flatten exam repository layout'
        git -C "$migration" push origin master
    fi
    rm -rf "$migration"
    touch /var/lib/examshell/layout-v2
fi

find /var/lib/examshell/git -type d -exec chmod 2775 {} \;
find /var/lib/examshell/git -type f -exec chmod g+rw {} \;
find /var/lib/examshell/git -name git-daemon-export-ok -exec chmod 664 {} \;

git daemon --reuseaddr --base-path=/var/lib/examshell/git --export-all \
    --listen=0.0.0.0 --port=9418 \
    --user=git --group=git /var/lib/examshell/git &

exec /usr/sbin/sshd -D -e
