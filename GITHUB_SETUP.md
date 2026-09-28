# GitHub 배포 체크리스트

1. 새 GitHub repository를 만듭니다.
2. 이 ZIP의 모든 파일을 업로드합니다. `.github/workflows/update-and-deploy.yml`은 반드시 유지해야 합니다.
3. Repository → Settings → Secrets and variables → Actions → New repository secret → `DART_API_KEY`를 등록합니다.
4. Repository → Settings → Pages → Source를 `GitHub Actions`로 선택합니다.
5. Actions → `DART data update and GitHub Pages deploy` → `Run workflow`로 최초 실행합니다.
6. 배포가 완료되면 `https://<username>.github.io/<repo>/` 주소를 확인합니다.
7. Repository → About → Edit repository details → Website에 위 Pages 주소를 입력합니다.
8. README.md의 `YOUR_GITHUB_USERNAME`과 `YOUR_REPOSITORY`를 실제 값으로 교체합니다.

## 업로드 시 주의

- `.DS_Store`, `__MACOSX`, `Thumbs.db`, `.idea`, `.vscode` 등 OS/IDE 메타파일은 포함하지 않습니다.
- 단, `.github/workflows/update-and-deploy.yml`은 GitHub Actions에 필요한 **의도적인 hidden directory**이므로 삭제하면 안 됩니다.
