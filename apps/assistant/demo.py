from __future__ import annotations

from dataclasses import dataclass

SUPPORTED_DEMO_TOPICS = [
    "Greeting and assistant introduction",
    "Property search guidance",
    "Viewing request guidance",
    "Rental application guidance",
    "Account verification guidance",
    "Property verification guidance",
    "Agent or landlord verification guidance",
    "Support and contact guidance",
    "Navigation to approved RealityNG routes",
]

DEMO_SUGGESTED_PROMPTS = [
    "Hello, what can you help me with?",
    "How do I find properties in Lagos?",
    "How do I request a viewing?",
    "How do I apply for a rental property?",
    "How do I verify my account?",
]

NAVIGATION_ALLOW_LIST = {
    "home": "/",
    "homepage": "/",
    "browse": "/properties",
    "properties": "/properties",
    "property search": "/properties",
    "saved properties": "/saved-properties",
    "saved": "/saved-properties",
    "dashboard": "/dashboard",
    "profile": "/settings/profile",
    "verification": "/verification",
    "sign in": "/auth/sign-in",
    "login": "/auth/sign-in",
    "sign up": "/auth/sign-up",
    "register": "/auth/sign-up",
    "list property": "/properties/new",
}


@dataclass(frozen=True)
class DemoAssistantResult:
    intent: str
    content: str
    navigation: dict | None = None

    @property
    def metadata(self) -> dict:
        payload = {"provider": "demo", "intent": self.intent}
        if self.navigation:
            payload["navigation"] = self.navigation
        return payload


def resolve_demo_navigation(message: str) -> dict | None:
    text = _normalize(message)
    if not any(word in text for word in ("go", "open", "take", "navigate", "show")):
        return None

    matches = [
        (label, path)
        for label, path in NAVIGATION_ALLOW_LIST.items()
        if label in text
    ]
    if not matches:
        return None

    label, path = max(matches, key=lambda item: len(item[0]))
    return {"target": label, "path": path}


def build_demo_response(message: str) -> DemoAssistantResult:
    text = _normalize(message)
    words = set(text.split())
    navigation = resolve_demo_navigation(message)
    if navigation:
        return DemoAssistantResult(
            intent="navigation",
            content=(
                f"You can continue in RealityNG at {navigation['path']}. "
                "I can only suggest approved app destinations in demo mode."
            ),
            navigation=navigation,
        )

    if words.intersection({"hello", "hi", "hey"}) or any(
        phrase in text for phrase in ("good morning", "good afternoon")
    ):
        return DemoAssistantResult(
            intent="greeting",
            content=(
                "Hello, I am the RealityNG Demo Assistant. I can guide you through "
                "property discovery, viewings, rental applications, verification, and support."
            ),
        )

    if any(
        word in text
        for word in (
            "account verification",
            "identity",
            "verify my account",
            "personal verification",
        )
    ):
        return DemoAssistantResult(
            intent="account_verification_guidance",
            content=(
                "Go to Verification from your dashboard, choose the verification type that "
                "matches your role, complete the required fields, upload evidence, and submit."
            ),
        )

    if any(
        word in text
        for word in (
            "property verification",
            "ownership",
            "title document",
            "verify property",
        )
    ):
        return DemoAssistantResult(
            intent="property_verification_guidance",
            content=(
                "Property owners can open the property verification flow, select the owned "
                "listing, upload ownership evidence, and track the review status."
            ),
        )

    if any(
        word in text
        for word in (
            "agent verification",
            "landlord verification",
            "cac",
            "agent",
            "landlord",
        )
    ):
        return DemoAssistantResult(
            intent="agent_landlord_verification_guidance",
            content=(
                "Agents and landlords can submit role-specific verification details from "
                "the Verification screen. Admin reviewers approve, reject, or request "
                "more information."
            ),
        )

    if any(
        word in text
        for word in (
            "search",
            "find",
            "browse",
            "property",
            "apartment",
            "land",
            "shortlet",
            "hotel",
        )
    ):
        return DemoAssistantResult(
            intent="property_search_guidance",
            content=(
                "Use Browse Properties to search approved listings by city, property type, "
                "listing type, price range, and keywords. In demo mode I will not invent "
                "properties, prices, or availability."
            ),
        )

    if any(word in text for word in ("viewing", "view", "inspection", "tour", "schedule")):
        return DemoAssistantResult(
            intent="viewing_guidance",
            content=(
                "Open a property, show interest, then request a physical or virtual viewing. "
                "The owner or agent can confirm, reschedule, complete, or cancel the request."
            ),
        )

    if any(word in text for word in ("application", "apply", "rent application", "rental")):
        return DemoAssistantResult(
            intent="rental_application_guidance",
            content=(
                "After reviewing a property or completing a viewing, use Apply for Property "
                "to submit your rental application. You can track its status from your dashboard."
            ),
        )

    if any(word in text for word in ("support", "contact", "help", "customer service")):
        return DemoAssistantResult(
            intent="support_contact_guidance",
            content=(
                "For support, use the account and property workflows in the dashboard first. "
                "If an issue still needs help, contact the RealityNG operations team through "
                "the approved support channel."
            ),
        )

    return DemoAssistantResult(
        intent="unsupported",
        content=(
            "I am currently a guided demo assistant. I can help with property search guidance, "
            "viewing requests, rental applications, verification, support, and approved app "
            "navigation. I cannot answer unsupported questions or fabricate private, legal, "
            "pricing, or listing details."
        ),
    )


def extract_demo_search_filters(query: str) -> dict:
    text = _normalize(query)
    filters: dict = {}

    for city in ("lagos", "lekki", "abuja", "uyo", "enugu", "ibadan", "port harcourt"):
        if city in text:
            filters["city"] = "Port Harcourt" if city == "port harcourt" else city.title()
            break

    property_types = {
        "land": "land",
        "duplex": "duplex",
        "apartment": "apartment",
        "shortlet": "shortlet",
        "commercial": "commercial",
        "hotel": "hotel",
    }
    for keyword, value in property_types.items():
        if keyword in text:
            filters["property_type"] = value
            break

    if "rent" in text or "rental" in text:
        filters["listing_type"] = "rent"
    elif "buy" in text or "sale" in text or "purchase" in text:
        filters["listing_type"] = "sale"

    return filters


def _normalize(value: str) -> str:
    return " ".join((value or "").lower().split())
