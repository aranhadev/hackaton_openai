FROM debian:bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/opt/examshell

# Build environment TLS inspection may not be trusted by the slim base image. APT still checks Debian archive signatures.
RUN sed -i 's|http://deb.debian.org|https://deb.debian.org|g' /etc/apt/sources.list.d/debian.sources \
 && apt-get -o Acquire::https::Verify-Peer=false update \
 && apt-get -o Acquire::https::Verify-Peer=false install -y --no-install-recommends \
    gcc git libc6-dev openssh-server python3 python3-requests \
 && rm -rf /var/lib/apt/lists/* \
 && rm -f /etc/ssh/ssh_host_* \
 && groupadd --system git \
 && useradd --create-home --shell /bin/bash --groups git exam \
 && useradd --system --create-home --shell /usr/bin/git-shell --gid git git \
 && install -d -m 0755 /run/sshd /opt/examshell /var/lib/examshell/git /var/lib/examshell/sessions \
 && git config --system user.name 'Exam Candidate' \
 && git config --system user.email 'exam@localhost'

COPY src/examshell /opt/examshell/examshell
COPY subjects /opt/examshell/subjects
COPY scripts/entrypoint.sh /usr/local/bin/examshell-entrypoint
COPY deploy/sshd_config /etc/ssh/sshd_config

RUN chmod 0755 /usr/local/bin/examshell-entrypoint \
 && chown -R root:root /opt/examshell \
 && chmod -R a-w /opt/examshell \
 && chmod 0755 /opt/examshell/examshell/cli.py \
 && ln -s /opt/examshell/examshell/cli.py /usr/local/bin/examshell \
 && ln -s /opt/examshell/examshell/cli.py /usr/local/bin/grademe \
 && ln -s /opt/examshell/examshell/cli.py /usr/local/bin/status \
 && ln -s /opt/examshell/examshell/cli.py /usr/local/bin/finish

EXPOSE 22 9418
ENTRYPOINT ["/usr/local/bin/examshell-entrypoint"]
