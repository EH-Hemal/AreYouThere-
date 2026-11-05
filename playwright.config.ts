import {defineConfig} from '@playwright/test';
export default defineConfig({testDir:'./tests',timeout:120000,expect:{timeout:15000},workers:1,reporter:[['list'],['html',{open:'never'}]],use:{channel:'chrome',baseURL:'http://127.0.0.1:5173',actionTimeout:10000,navigationTimeout:15000,screenshot:'only-on-failure',trace:'retain-on-failure'},outputDir:'test-results'});
