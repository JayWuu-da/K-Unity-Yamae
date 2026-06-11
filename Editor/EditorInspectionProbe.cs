#if UNITY_EDITOR

using System.Collections.Generic;
using System.IO;
using System.Reflection;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Events;
using UnityEngine.SceneManagement;

namespace KUnityYamae.Editor
{
    public static class EditorInspectionProbe
    {
        internal sealed class ListenerFact
        {
            public string AssetPath = "";
            public string GameObjectPath = "";
            public string ComponentType = "";
            public string MethodName = "";
            public string TargetAssetPath = "";
            public string TargetType = "";
        }

        internal sealed class MissingReferenceFact
        {
            public string AssetPath = "";
            public string GameObjectPath = "";
            public string ComponentType = "";
            public string PropertyPath = "";
        }

        internal sealed class PrefabOverrideFact
        {
            public string ScenePath = "";
            public string GameObjectPath = "";
            public string SourcePrefabPath = "";
            public int ModifiedPropertyCount;
            public int AddedComponentCount;
            public int RemovedComponentCount;
        }

        internal sealed class UiComponentStateFact
        {
            public string AssetPath = "";
            public string GameObjectPath = "";
            public string ComponentType = "";
            public string Interactable = "";
            public string RaycastTarget = "";
            public string BlocksRaycasts = "";
        }

        public static void WriteReport()
        {
            var listeners = new List<ListenerFact>();
            var missingReferences = new List<MissingReferenceFact>();
            var overrides = new List<PrefabOverrideFact>();
            var uiComponentStates = new List<UiComponentStateFact>();

            InspectPrefabs(listeners, missingReferences, uiComponentStates);
            InspectScenes(listeners, missingReferences, overrides, uiComponentStates);

            var output = Path.Combine(Application.dataPath, "..", ".unity-harness", "reports");
            Directory.CreateDirectory(output);
            var reportPath = Path.Combine(output, "editor-inspection.json");
            File.WriteAllText(
                reportPath,
                EditorInspectionJson.Build(listeners, missingReferences, overrides, uiComponentStates),
                System.Text.Encoding.UTF8);
            Debug.Log($"[K-Unity-Yamae] Editor inspection written: {reportPath}");
        }

        private static void InspectPrefabs(
            List<ListenerFact> listeners,
            List<MissingReferenceFact> missingReferences,
            List<UiComponentStateFact> uiComponentStates)
        {
            foreach (var guid in AssetDatabase.FindAssets("t:Prefab"))
            {
                var assetPath = AssetDatabase.GUIDToAssetPath(guid);
                var root = PrefabUtility.LoadPrefabContents(assetPath);
                try
                {
                    InspectGameObjectTree(root, assetPath, listeners, missingReferences, uiComponentStates);
                }
                finally
                {
                    PrefabUtility.UnloadPrefabContents(root);
                }
            }
        }

        private static void InspectScenes(
            List<ListenerFact> listeners,
            List<MissingReferenceFact> missingReferences,
            List<PrefabOverrideFact> overrides,
            List<UiComponentStateFact> uiComponentStates)
        {
            foreach (var guid in AssetDatabase.FindAssets("t:Scene"))
            {
                var scenePath = AssetDatabase.GUIDToAssetPath(guid);
                var scene = EditorSceneManager.OpenScene(scenePath, OpenSceneMode.Single);
                if (!scene.IsValid())
                {
                    continue;
                }

                foreach (var root in scene.GetRootGameObjects())
                {
                    InspectGameObjectTree(root, scenePath, listeners, missingReferences, uiComponentStates);
                    InspectPrefabOverrides(root, scenePath, overrides);
                }
            }
        }

        private static void InspectGameObjectTree(
            GameObject root,
            string assetPath,
            List<ListenerFact> listeners,
            List<MissingReferenceFact> missingReferences,
            List<UiComponentStateFact> uiComponentStates)
        {
            foreach (var component in root.GetComponentsInChildren<Component>(true))
            {
                if (component == null)
                {
                    continue;
                }

                InspectUnityEvents(component, assetPath, listeners);
                InspectSerializedObject(component, assetPath, listeners, missingReferences);
                InspectUiComponentState(component, assetPath, uiComponentStates);
            }
        }

        private static void InspectUiComponentState(
            Component component,
            string assetPath,
            List<UiComponentStateFact> uiComponentStates)
        {
            var isSelectable = IsTypeOrBase(component.GetType(), "UnityEngine.UI.Selectable");
            var isGraphic = IsTypeOrBase(component.GetType(), "UnityEngine.UI.Graphic");
            var canvasGroup = component as CanvasGroup;
            if (!isSelectable && !isGraphic && canvasGroup == null)
            {
                return;
            }

            uiComponentStates.Add(new UiComponentStateFact
            {
                AssetPath = assetPath,
                GameObjectPath = GetGameObjectPath(component.gameObject),
                ComponentType = component.GetType().FullName,
                Interactable = isSelectable ? ReadBooleanProperty(component, "interactable") : "",
                RaycastTarget = isGraphic ? ReadBooleanProperty(component, "raycastTarget") : "",
                BlocksRaycasts = canvasGroup != null ? canvasGroup.blocksRaycasts.ToString() : ""
            });
        }

        private static bool IsTypeOrBase(System.Type type, string fullName)
        {
            var current = type;
            while (current != null)
            {
                if (current.FullName == fullName)
                {
                    return true;
                }

                current = current.BaseType;
            }

            return false;
        }

        private static string ReadBooleanProperty(Component component, string propertyName)
        {
            const BindingFlags Flags = BindingFlags.Instance | BindingFlags.Public;
            var property = component.GetType().GetProperty(propertyName, Flags);
            if (property == null || property.PropertyType != typeof(bool) || !property.CanRead)
            {
                return "";
            }

            return property.GetValue(component).ToString();
        }

        private static void InspectUnityEvents(
            Component component,
            string assetPath,
            List<ListenerFact> listeners)
        {
            const BindingFlags Flags = BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic;
            foreach (var field in component.GetType().GetFields(Flags))
            {
                if (!typeof(UnityEventBase).IsAssignableFrom(field.FieldType))
                {
                    continue;
                }

                AddUnityEventFacts(component, assetPath, (UnityEventBase)field.GetValue(component), listeners);
            }

            foreach (var property in component.GetType().GetProperties(Flags))
            {
                if (!typeof(UnityEventBase).IsAssignableFrom(property.PropertyType) ||
                    property.GetIndexParameters().Length > 0 ||
                    !property.CanRead)
                {
                    continue;
                }

                AddUnityEventFacts(component, assetPath, (UnityEventBase)property.GetValue(component), listeners);
            }
        }

        private static void AddUnityEventFacts(
            Component component,
            string assetPath,
            UnityEventBase unityEvent,
            List<ListenerFact> listeners)
        {
            if (unityEvent == null)
            {
                return;
            }

            for (var i = 0; i < unityEvent.GetPersistentEventCount(); i++)
            {
                var target = unityEvent.GetPersistentTarget(i);
                if (target == null)
                {
                    continue;
                }

                listeners.Add(new ListenerFact
                {
                    AssetPath = assetPath,
                    GameObjectPath = GetGameObjectPath(component.gameObject),
                    ComponentType = component.GetType().FullName,
                    MethodName = unityEvent.GetPersistentMethodName(i),
                    TargetAssetPath = AssetDatabase.GetAssetPath(target),
                    TargetType = target.GetType().FullName
                });
            }
        }

        private static void InspectSerializedObject(
            Component component,
            string assetPath,
            List<ListenerFact> listeners,
            List<MissingReferenceFact> missingReferences)
        {
            var serialized = new SerializedObject(component);
            var property = serialized.GetIterator();
            while (property.NextVisible(true))
            {
                if (property.propertyType == SerializedPropertyType.ObjectReference &&
                    property.objectReferenceValue == null &&
                    property.objectReferenceInstanceIDValue != 0)
                {
                    missingReferences.Add(new MissingReferenceFact
                    {
                        AssetPath = assetPath,
                        GameObjectPath = GetGameObjectPath(component.gameObject),
                        ComponentType = component.GetType().FullName,
                        PropertyPath = property.propertyPath
                    });
                }
            }
        }

        private static void InspectPrefabOverrides(
            GameObject root,
            string scenePath,
            List<PrefabOverrideFact> overrides)
        {
            foreach (var transform in root.GetComponentsInChildren<Transform>(true))
            {
                var instanceRoot = PrefabUtility.GetNearestPrefabInstanceRoot(transform.gameObject);
                if (instanceRoot == null || instanceRoot != transform.gameObject)
                {
                    continue;
                }

                var source = PrefabUtility.GetCorrespondingObjectFromSource(instanceRoot);
                var modifications = PrefabUtility.GetPropertyModifications(instanceRoot);
                var addedComponents = PrefabUtility.GetAddedComponents(instanceRoot);
                var removedComponents = PrefabUtility.GetRemovedComponents(instanceRoot);
                overrides.Add(new PrefabOverrideFact
                {
                    ScenePath = scenePath,
                    GameObjectPath = GetGameObjectPath(instanceRoot),
                    SourcePrefabPath = source != null ? AssetDatabase.GetAssetPath(source) : "",
                    ModifiedPropertyCount = modifications != null ? modifications.Length : 0,
                    AddedComponentCount = addedComponents != null ? addedComponents.Length : 0,
                    RemovedComponentCount = removedComponents != null ? removedComponents.Length : 0
                });
            }
        }

        private static string GetGameObjectPath(GameObject gameObject)
        {
            var names = new List<string>();
            var current = gameObject.transform;
            while (current != null)
            {
                names.Add(current.name);
                current = current.parent;
            }

            names.Reverse();
            return string.Join("/", names);
        }
    }
}

#endif
