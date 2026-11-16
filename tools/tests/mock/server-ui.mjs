export class ActionFormData {
  title() { return this; } body() { return this; } button() { return this; } divider() { return this; } header() { return this; } label() { return this; }
  show() { return Promise.resolve({ canceled: true }); }
}
