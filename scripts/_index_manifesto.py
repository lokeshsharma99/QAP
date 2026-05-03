"""Index the GDS Demo App Site Manifesto into PgVector via Knowledge.ainsert_many."""
import asyncio
import json

from contracts.site_manifesto import SiteManifesto
from db.session import create_knowledge


def _build_insert_args(manifesto: SiteManifesto, raw_data: dict) -> list[dict]:
    """Build list of dicts compatible with Knowledge.ainsert_many."""
    args: list[dict] = []
    for page in manifesto.pages:
        parts = [
            f"Page: {page.title}",
            f"URL: {page.url}",
            f"Route: {page.route}",
            f"Type: {page.page_type}",
            f"Auth required: {page.is_auth_gated}",
            "",
            "Components:",
        ]
        for comp in page.components:
            locators = []
            if comp.css_selector:
                locators.append(f"css:{comp.css_selector}")
            if comp.role_locator:
                locators.append(f"role:{comp.role_locator}")
            if comp.text_locator:
                locators.append(f"text:{comp.text_locator}")
            parts.append(
                f"  - [{comp.component_type}] {comp.component_id}"
                f' | label="{comp.aria_label}"'
                f' | {" | ".join(locators)}'
            )
        args.append({
            "name": page.title,
            "text_content": "\n".join(parts),
            "metadata": {
                "source": "site_manifesto",
                "manifesto_id": manifesto.manifesto_id,
                "aut": manifesto.aut_base_url,
                "page_id": page.page_id,
                "route": page.route,
                "page_type": page.page_type,
            },
            "upsert": True,
        })

    # Full manifesto as one searchable document
    args.append({
        "name": f"Full Site Manifesto: {manifesto.aut_name}",
        "text_content": json.dumps(raw_data, indent=2),
        "metadata": {
            "source": "site_manifesto",
            "manifesto_id": manifesto.manifesto_id,
            "aut": manifesto.aut_base_url,
            "type": "full_manifesto",
        },
        "upsert": True,
    })
    return args


async def main() -> None:
    with open("generated/site_manifesto_gds_demo_app.json") as f:
        raw = json.load(f)

    manifesto = SiteManifesto(**raw)
    manifesto.calculate_statistics()

    kb = create_knowledge("Site Manifesto", "site_manifesto_vectors")
    insert_args = _build_insert_args(manifesto, raw)

    await kb.ainsert_many(insert_args, upsert=True)
    print(f"Indexed {len(insert_args)} documents into site_manifesto_vectors")
    print(f"  pages: {manifesto.total_pages}, components: {manifesto.total_components}")


if __name__ == "__main__":
    asyncio.run(main())
