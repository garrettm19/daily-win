const path = require("path");

// Expo SDK 57 internal type-generation entry. Update this require if an SDK
// bump moves @expo/cli's startTypescriptTypeGeneration module.
const projectRoot = path.resolve(__dirname, "..");
const { startTypescriptTypeGenerationAsync } = require(
  require.resolve(
    "@expo/cli/build/src/start/server/type-generation/startTypescriptTypeGeneration",
    { paths: [require.resolve("expo/package.json")] },
  ),
);

startTypescriptTypeGenerationAsync({ projectRoot }).catch((error) => {
  console.error(error);
  process.exit(1);
});
