# Daily Win mobile

Expo SDK 57 app for Daily Win. Physical iOS development uses an **Expo development build** (`expo-dev-client`), not App Store Expo Go. Current Expo Go does not include the SDK 57 native modules this app needs.

## Get started

From this directory:

```bash
npm start
```

That starts Metro for the development client (`expo start --dev-client`).

Web (optional):

```bash
npm run web
```

This project uses [file-based routing](https://docs.expo.dev/router/introduction) in `src/app`.

API base URL comes from `EXPO_PUBLIC_API_URL` in `.env.local` (copy `.env.example`). Do not commit `.env.local`. Restart Metro after changing it.

## iOS development build

Windows cannot compile an iOS binary locally. Use EAS to build the development client, then install it on the iPhone and connect it to Metro.

Prerequisites (Mason):

1. An Expo account, then `npx eas-cli login` from `apps/mobile`
2. EAS CLI (`npm install -g eas-cli` or `npx eas-cli`)
3. Active Apple Developer Program membership
4. The iPhone registered on the Apple Developer team
5. iOS Developer Mode enabled on the iPhone
6. First-time EAS project link: `npx eas-cli init` (creates `extra.eas.projectId`; requires Expo login)

Then:

```bash
cd apps/mobile
npx eas-cli build --platform ios --profile development
```

After the build installs on the phone:

```bash
npx expo start --dev-client
```

Open the Daily Win development client and connect to that Metro session. Do not use Expo Go.

This repository does not configure App Store or TestFlight production submission.
