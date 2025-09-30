module.exports = {
  apps: [{
    name: 'ecoful-chat',
    script: 'npx',
    args: 'vite preview --host 0.0.0.0 --port 3000',
    cwd: '/var/www/ecoful-chat',
    instances: 2,
    exec_mode: 'cluster',
    env: {
      NODE_ENV: 'production',
      PORT: 3000
    },
    env_production: {
      NODE_ENV: 'production',
      PORT: 3000
    },
    error_file: '/var/log/pm2/ecoful-chat-error.log',
    out_file: '/var/log/pm2/ecoful-chat-out.log',
    log_file: '/var/log/pm2/ecoful-chat.log',
    time: true,
    autorestart: true,
    watch: false,
    max_memory_restart: '1G',
    min_uptime: '10s',
    max_restarts: 5,
    restart_delay: 4000
  }]
}