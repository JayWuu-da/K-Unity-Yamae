#if UNITY_EDITOR

using System.Collections.Generic;
using System.Text;

namespace KUnityYamae.Editor
{
    internal static class EditorInspectionJson
    {
        public static string Build(
            List<EditorInspectionProbe.ListenerFact> listeners,
            List<EditorInspectionProbe.MissingReferenceFact> missingReferences,
            List<EditorInspectionProbe.PrefabOverrideFact> overrides,
            List<EditorInspectionProbe.UiComponentStateFact> uiComponentStates)
        {
            var json = new StringBuilder();
            json.Append("{");
            AppendString(json, "schema", "unity-harness.editor-inspection.v1");
            json.Append(",");
            AppendString(json, "generatedBy", "KUnityYamae.Editor.HarnessChecks.RunEditorInspection");
            json.Append(",");
            AppendInspectorConnections(json, listeners);
            json.Append(",");
            AppendPrefabOverrides(json, overrides);
            json.Append(",");
            AppendSerializedReferences(json, missingReferences);
            json.Append(",");
            AppendUiComponentStates(json, uiComponentStates);
            json.Append("}");
            return json.ToString();
        }

        private static void AppendInspectorConnections(
            StringBuilder json,
            List<EditorInspectionProbe.ListenerFact> listeners)
        {
            json.Append("\"inspectorConnections\":{");
            AppendNumber(json, "persistentListenerCount", listeners.Count);
            json.Append(",\"listeners\":[");
            for (var i = 0; i < listeners.Count; i++)
            {
                if (i > 0) json.Append(",");
                json.Append("{");
                AppendString(json, "assetPath", listeners[i].AssetPath);
                json.Append(",");
                AppendString(json, "gameObjectPath", listeners[i].GameObjectPath);
                json.Append(",");
                AppendString(json, "componentType", listeners[i].ComponentType);
                json.Append(",");
                AppendString(json, "methodName", listeners[i].MethodName);
                json.Append(",");
                AppendString(json, "targetAssetPath", listeners[i].TargetAssetPath);
                json.Append(",");
                AppendString(json, "targetType", listeners[i].TargetType);
                json.Append("}");
            }

            json.Append("]}");
        }

        private static void AppendPrefabOverrides(
            StringBuilder json,
            List<EditorInspectionProbe.PrefabOverrideFact> overrides)
        {
            var modifiedCount = 0;
            var addedCount = 0;
            var removedCount = 0;
            foreach (var item in overrides)
            {
                modifiedCount += item.ModifiedPropertyCount;
                addedCount += item.AddedComponentCount;
                removedCount += item.RemovedComponentCount;
            }

            json.Append("\"prefabOverrides\":{");
            AppendNumber(json, "instanceCount", overrides.Count);
            json.Append(",");
            AppendNumber(json, "modifiedPropertyCount", modifiedCount);
            json.Append(",");
            AppendNumber(json, "removedComponentCount", removedCount);
            json.Append(",");
            AppendNumber(json, "addedComponentCount", addedCount);
            json.Append(",\"instances\":[");
            for (var i = 0; i < overrides.Count; i++)
            {
                if (i > 0) json.Append(",");
                json.Append("{");
                AppendString(json, "scenePath", overrides[i].ScenePath);
                json.Append(",");
                AppendString(json, "gameObjectPath", overrides[i].GameObjectPath);
                json.Append(",");
                AppendString(json, "sourcePrefabPath", overrides[i].SourcePrefabPath);
                json.Append(",");
                AppendNumber(json, "modifiedPropertyCount", overrides[i].ModifiedPropertyCount);
                json.Append(",");
                AppendNumber(json, "addedComponentCount", overrides[i].AddedComponentCount);
                json.Append(",");
                AppendNumber(json, "removedComponentCount", overrides[i].RemovedComponentCount);
                json.Append("}");
            }

            json.Append("]}");
        }

        private static void AppendSerializedReferences(
            StringBuilder json,
            List<EditorInspectionProbe.MissingReferenceFact> missingReferences)
        {
            json.Append("\"serializedReferences\":{");
            AppendNumber(json, "missingObjectReferenceCount", missingReferences.Count);
            json.Append(",\"missingReferences\":[");
            for (var i = 0; i < missingReferences.Count; i++)
            {
                if (i > 0) json.Append(",");
                json.Append("{");
                AppendString(json, "assetPath", missingReferences[i].AssetPath);
                json.Append(",");
                AppendString(json, "gameObjectPath", missingReferences[i].GameObjectPath);
                json.Append(",");
                AppendString(json, "componentType", missingReferences[i].ComponentType);
                json.Append(",");
                AppendString(json, "propertyPath", missingReferences[i].PropertyPath);
                json.Append("}");
            }

            json.Append("]}");
        }

        private static void AppendUiComponentStates(
            StringBuilder json,
            List<EditorInspectionProbe.UiComponentStateFact> uiComponentStates)
        {
            json.Append("\"uiComponentStates\":{");
            AppendNumber(json, "componentCount", uiComponentStates.Count);
            json.Append(",\"components\":[");
            for (var i = 0; i < uiComponentStates.Count; i++)
            {
                if (i > 0) json.Append(",");
                json.Append("{");
                AppendString(json, "assetPath", uiComponentStates[i].AssetPath);
                json.Append(",");
                AppendString(json, "gameObjectPath", uiComponentStates[i].GameObjectPath);
                json.Append(",");
                AppendString(json, "componentType", uiComponentStates[i].ComponentType);
                json.Append(",");
                AppendString(json, "interactable", uiComponentStates[i].Interactable);
                json.Append(",");
                AppendString(json, "raycastTarget", uiComponentStates[i].RaycastTarget);
                json.Append(",");
                AppendString(json, "blocksRaycasts", uiComponentStates[i].BlocksRaycasts);
                json.Append("}");
            }

            json.Append("]}");
        }

        private static void AppendString(StringBuilder json, string key, string value)
        {
            json.Append("\"").Append(Escape(key)).Append("\":\"").Append(Escape(value)).Append("\"");
        }

        private static void AppendNumber(StringBuilder json, string key, int value)
        {
            json.Append("\"").Append(Escape(key)).Append("\":").Append(value);
        }

        private static string Escape(string value)
        {
            return value
                .Replace("\\", "\\\\")
                .Replace("\"", "\\\"")
                .Replace("\r", "\\r")
                .Replace("\n", "\\n");
        }
    }
}

#endif
