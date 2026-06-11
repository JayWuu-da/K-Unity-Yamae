#if UNITY_EDITOR

using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;
using System.Linq;

namespace KUnityYamae.Editor
{
    public static class HarnessChecks
    {
        public static void RunAll()
        {
            ValidateNoMissingScriptsInBuildScenes();
            ValidateRequiredScriptableObjects();
            ValidateNoDuplicateAddresses();
            Debug.Log("HARNESS_CHECKS_COMPLETE");
        }

        public static void RunEditorInspection()
        {
            EditorInspectionProbe.WriteReport();
            Debug.Log("HARNESS_EDITOR_INSPECTION_COMPLETE");
        }

        private static void ValidateNoMissingScriptsInBuildScenes()
        {
            var buildScenes = EditorBuildSettings.scenes
                .Where(s => s.enabled)
                .Select(s => s.path)
                .ToArray();

            if (buildScenes.Length == 0)
            {
                Debug.LogWarning("[HarnessChecks] No build scenes configured.");
                return;
            }

            int missingCount = 0;
            foreach (var scenePath in buildScenes)
            {
                if (string.IsNullOrEmpty(scenePath)) continue;

                var scene = EditorSceneManager.GetSceneByPath(scenePath);
                if (!scene.IsValid())
                {
                    if (!EditorSceneManager.OpenScene(scenePath, OpenSceneMode.Single))
                    {
                        Debug.LogError($"[HarnessChecks] Failed to open scene: {scenePath}");
                        missingCount++;
                        continue;
                    }
                    scene = EditorSceneManager.GetSceneByPath(scenePath);
                }

                foreach (var root in scene.GetRootGameObjects())
                {
                    var components = root.GetComponentsInChildren<Component>(true);
                    foreach (var comp in components)
                    {
                        if (comp == null)
                        {
                            Debug.LogError($"[HarnessChecks] Missing script on GameObject: {root.name} in scene {scenePath}");
                            missingCount++;
                        }
                    }
                }
            }

            if (missingCount > 0)
                Debug.LogError($"[HarnessChecks] Found {missingCount} missing script(s) in build scenes.");
            else
                Debug.Log("[HarnessChecks] No missing scripts in build scenes.");
        }

        private static void ValidateRequiredScriptableObjects()
        {
            var guids = AssetDatabase.FindAssets("t:ScriptableObject");
            int count = guids.Length;
            Debug.Log($"[HarnessChecks] Found {count} ScriptableObject assets in project.");

            foreach (var guid in guids)
            {
                var path = AssetDatabase.GUIDToAssetPath(guid);
                var so = AssetDatabase.LoadAssetAtPath<ScriptableObject>(path);
                if (so == null)
                {
                    Debug.LogWarning($"[HarnessChecks] ScriptableObject at {path} failed to load.");
                }
            }
        }

        private static void ValidateNoDuplicateAddresses()
        {
            Debug.Log("[HarnessChecks] Addressable key validation skipped (requires Addressables package).");
        }
    }
}

#endif
