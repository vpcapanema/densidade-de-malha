@echo off
setlocal
cd /d "D:\densidade _de_malha"
set RENDER_API_KEY=rnd_EuGyhhngRII85XsgYwJTRitPxn2d
node tools/render-create-static-site.mjs --owner-name "My Workspace"
pause
