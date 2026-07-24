"""Menu manager (M6), rebuilt as the design system's golden screen
(ADR-0055): task-first master-detail — see the navigation, select an
item, edit it. Defined items replace the derived menu entirely on the
next build; with none, the derived menu (home anchors + blog +
published pages) keeps working.

The editor renders only on selection or on an explicit "Add item"
(DS-16, DS-18); translations and technical fields live in closed
disclosures (DS-8, DS-17); the empty state carries the next action
(DS-7).
"""

import re

from cms_core import Language, MenuItem, Role, User
from cms_core.accounts import AdminSession
from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import RedirectResponse

from cms_admin.auth import current_session, enforce_csrf, get_db, require_at_least
from cms_admin.navigation import AdminScreen, register_screen

router = APIRouter(prefix="/menu")

register_screen(AdminScreen("menu", "/menu", "Menu", "bi-list-nested", 140))

_REQUIRE_PUBLISHER = require_at_least(Role.PUBLISHER)

HTTP_422 = status.HTTP_422_UNPROCESSABLE_CONTENT


def _slug_from(text: str) -> str:
    """A lowercase-with-dashes id derived from a label or URL, so adding
    an item needs no technical input (the id stays editable under
    Advanced)."""
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug or "item"


async def _page(request: Request, context: dict[str, object], status_code: int = 200) -> object:
    items = await get_db(request).run(lambda storage: storage.load_menu_items())
    query = str(request.query_params.get("q", "")).strip()
    shown = [
        item
        for item in items
        if not query
        or query.lower() in item.id.lower()
        or query.lower() in item.url.lower()
        or any(query.lower() in label.lower() for label in item.labels.values())
    ]
    selected_id = str(request.query_params.get("item", "")).strip()
    # Canonical-identifier rule: the raw parameter only ever resolves
    # against the loaded items; downstream use takes the object.
    selected = next((item for item in items if item.id == selected_id), None)
    editing = selected is not None or request.query_params.get("new") is not None
    return request.app.state.templates.TemplateResponse(
        request,
        "menu.html.j2",
        {
            "active_section": "menu",
            "items": items,
            "shown_items": shown,
            "query": query,
            "selected": selected,
            "editing": editing,
            "languages": list(Language),
            **context,
        },
        status_code=status_code,
    )


@router.get("")
async def menu_list(
    request: Request,
    user_session: tuple[User, AdminSession] = Depends(current_session),
) -> object:
    user, session = user_session
    return await _page(request, {"user": user, "csrf_token": session.csrf_token, "errors": []})


@router.post("")
async def menu_save(
    request: Request,
    _role: tuple[User, AdminSession] = Depends(_REQUIRE_PUBLISHER),
    user_session: tuple[User, AdminSession] = Depends(enforce_csrf),
) -> object:
    user, session = user_session
    form = await request.form()
    labels = {
        language: str(form.get(f"label_{language.value}", "")).strip()
        for language in Language
        if str(form.get(f"label_{language.value}", "")).strip()
    }
    item_id = str(form.get("id", "")).strip()
    url = str(form.get("url", "")).strip()
    if not item_id:
        source = next(iter(labels.values()), "") or url
        item_id = _slug_from(source)
    try:
        item = MenuItem(
            id=item_id,
            url=url,
            position=int(str(form.get("position", "0") or "0")),
            labels=labels,
        )
    except (ValueError, TypeError):
        return await _page(
            request,
            {
                "user": user,
                "csrf_token": session.csrf_token,
                "errors": ["menu: id is lowercase-with-dashes, url and position are required"],
            },
            status_code=HTTP_422,
        )
    await get_db(request).run(lambda storage: storage.save_menu_item(item))
    return RedirectResponse(f"/menu?item={item.id}", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/{item_id}/move")
async def menu_move(
    request: Request,
    item_id: str,
    _role: tuple[User, AdminSession] = Depends(_REQUIRE_PUBLISHER),
    user_session: tuple[User, AdminSession] = Depends(enforce_csrf),
    direction: str = Form(...),
) -> RedirectResponse:
    """Reorder by swapping positions with the neighbor — the list is the
    ordering surface (golden screen), not a numeric field."""
    items = await get_db(request).run(lambda storage: storage.load_menu_items())
    index = next((i for i, item in enumerate(items) if item.id == item_id), None)
    if index is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="unknown menu item")
    swap = index - 1 if direction == "up" else index + 1
    if 0 <= swap < len(items):
        order = list(items)
        order[index], order[swap] = order[swap], order[index]
        # Renumber 1..n: deterministic, and it heals duplicate positions.
        moved = [item.model_copy(update={"position": i + 1}) for i, item in enumerate(order)]
        await get_db(request).run(lambda storage: [storage.save_menu_item(item) for item in moved])
    return RedirectResponse("/menu", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/{item_id}/delete")
async def menu_delete(
    request: Request,
    item_id: str,
    _role: tuple[User, AdminSession] = Depends(_REQUIRE_PUBLISHER),
    user_session: tuple[User, AdminSession] = Depends(enforce_csrf),
) -> RedirectResponse:
    deleted = await get_db(request).run(lambda storage: storage.delete_menu_item(item_id))
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="unknown menu item")
    return RedirectResponse("/menu", status_code=status.HTTP_303_SEE_OTHER)
