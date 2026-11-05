import {defineConfig} from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';
export default defineConfig({plugins:[react(),tailwindcss()],base:'./',publicDir:false,build:{outDir:'dist/extension',rollupOptions:{input:{panel:'extension/panel.html',background:'extension/background.ts'},output:{entryFileNames:'[name].js',chunkFileNames:'assets/[name]-[hash].js'}}}});
