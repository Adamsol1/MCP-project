class KnowledgeService:
    # Sort URIs based on the priority of their categories

    def __init__(self, registry: dict) -> None:
        self.registry = registry

    def get_relevant_resources(self, text: str) -> list[str]:
        """Return a list of KB URIs relevant to the input text."""
        if text.strip() == "":
            return []  # Return if empty

        text_lower = text.lower()
        relevant_uris = {}

        # Check if any words in the keyword are present in the text (case-insensitive)
        for entry in self.registry.values():
            for keyword in entry["keywords"]:
                if keyword.lower() in text_lower:
                    relevant_uris[entry["path"]] = entry["category"]
                    break  # No need to check other keywords for this entry

        # Sort URIs based on the priority of their priority in knowledge_registry
        # The sorting is done by looking up the priority of each URI in the registry.
        sorted_uris = sorted(
            relevant_uris.keys(),
            key=lambda uri: next(
                entry["priority"]
                for entry in self.registry.values()
                if entry["path"] == uri
            ),
        )
        return sorted_uris[:5]  # Return top 5 results
