import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { loadEnv } from 'vite';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';
var frontendRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..');
var projectRoot = resolve(frontendRoot, '..');
export default defineConfig(function (_a) {
    var mode = _a.mode;
    var env = loadEnv(mode, projectRoot, '');
    var frontendPort = Number(env.FRONTEND_PORT || '5173');
    var backendPort = Number(env.BACKEND_PORT || '8000');
    return {
        plugins: [react()],
        server: {
            port: frontendPort,
            proxy: {
                '/api': "http://localhost:".concat(backendPort),
            },
        },
    };
});
