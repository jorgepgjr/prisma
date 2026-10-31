import { afterEach } from "vitest";
import { cleanup } from "@testing-library/react";

// DOM-only tests: no browser navigation or external image requests.
Object.defineProperty(HTMLDialogElement.prototype, "showModal", { configurable: true, value() { this.setAttribute("open", ""); } });
Object.defineProperty(HTMLDialogElement.prototype, "close", { configurable: true, value() { this.removeAttribute("open"); } });
afterEach(() => cleanup());
