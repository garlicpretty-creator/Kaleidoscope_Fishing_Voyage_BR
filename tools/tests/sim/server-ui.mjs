// Forms record what they would show and answer with a scripted selection (or "closed").
import { __log } from './server.mjs';

export const __answers = [];
export class ActionFormData {
  constructor() { this.form = { title: undefined, body: undefined, buttons: [] }; }
  title(t) { this.form.title = t; return this; }
  body(b) { this.form.body = b; return this; }
  button(t, icon) { this.form.buttons.push({ t, icon }); return this; }
  divider() { return this; }
  header(t) { this.form.buttons; return this; }
  label() { return this; }
  show() {
    __log.forms.push(this.form);
    const a = __answers.shift();
    return Promise.resolve(a === undefined ? { canceled: true, cancelationReason: 'UserClosed' } : { canceled: false, selection: a });
  }
}
