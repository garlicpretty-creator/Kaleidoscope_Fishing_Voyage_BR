// ## 1.6.0: how the journal's picture pages are drawn (docs/PLAN_1.6.0.md 6.6, approach B).
// Vanilla ActionFormData with nothing but glyph characters, the symbols ◆ ✿ ✦ ★ and white space in the title,
// body and buttons. Button icons (pictures) stay. A long list is cut into pages of PAGE buttons, turned with the
// arrow.left / arrow.right glyph buttons; the body ends with one dot per page, the current one filled up to it.
import { ActionFormData } from "@minecraft/server-ui";
import { G, dots } from "../data/glyphs.js";

/** The form title: one space, so the frame shows an empty title bar (6.6 #1). */
export const TITLE = " ";
export const PAGE = 20;
export const BACK = G["arrow.up"];
export const PREV = G["arrow.left"];
export const NEXT = G["arrow.right"];

/**
 * A glyph body laid out for the form: a glyph draws about 1.5 text lines tall, so each line of glyphs gets an empty
 * line under it and the body starts with one (else the rows overlap and the first is cut by the panel's top edge).
 */
export function spaced(body) {
  return body ? "\n" + body.split("\n").join("\n\n") : body;
}

export function pageSound(player) { try { player.playSound("item.book.page_turn", { volume: 0.8 }); } catch {} }

/** A page with only a body and the back button. Resolves true for back, false when closed. */
export async function showPlain(player, body) {
  const res = await new ActionFormData().title(TITLE).body(spaced(body)).button(BACK).show(player);
  if (res.canceled || res.selection === undefined) return false;
  pageSound(player);
  return true;
}

/**
 * A list of buttons ({ text, icon }), PAGE to a page. Resolves { pick, page } for an item (its index in `items`),
 * { back: true, page } for the back button, or undefined when the form is closed. Turning a page shows the next
 * form itself.
 */
export async function showPaged(player, { body = "", items, page = 0, back = true }) {
  const pages = Math.max(1, Math.ceil(items.length / PAGE));
  page = Math.max(0, Math.min(pages - 1, Math.floor(Number(page) || 0)));
  const form = new ActionFormData().title(TITLE).body(spaced(pages > 1 ? `${body}${body ? "\n" : ""}${dots(page + 1, pages)}` : body));
  const actions = [];
  items.slice(page * PAGE, (page + 1) * PAGE).forEach((it, i) => {
    form.button(it.text, it.icon);
    actions.push({ pick: page * PAGE + i });
  });
  if (page > 0) { form.button(PREV); actions.push({ turn: page - 1 }); }
  if (page < pages - 1) { form.button(NEXT); actions.push({ turn: page + 1 }); }
  if (back) { form.button(BACK); actions.push({ back: true }); }
  const res = await form.show(player);
  if (res.canceled || res.selection === undefined) return undefined;
  const a = actions[res.selection];
  if (!a) return undefined;
  pageSound(player);
  if (a.turn !== undefined) return showPaged(player, { body, items, page: a.turn, back });
  return { ...a, page };
}
