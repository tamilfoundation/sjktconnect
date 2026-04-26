import "@testing-library/jest-dom";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import SuggestForm from "@/components/SuggestForm";
import { PhotoUploadError } from "@/lib/api";

// Reuse the real PhotoUploadError so `instanceof` checks inside SuggestForm
// match the error our test throws. Stub only the network-call functions.
jest.mock("@/lib/api", () => {
  const actual = jest.requireActual("@/lib/api");
  return {
    ...actual,
    createSuggestion: jest.fn().mockResolvedValue({}),
    uploadSchoolPhoto: jest.fn(),
  };
});

import * as api from "@/lib/api";
const uploadMock = api.uploadSchoolPhoto as jest.Mock;

URL.createObjectURL = jest.fn(() => "blob:preview");
URL.revokeObjectURL = jest.fn();

// jsdom doesn't decode the blob URL, so the Image dimension probe never fires
// onload organically. Stub the Image constructor to immediately report a
// happy-path 800×600 so validateAndSetFile keeps the file staged.
beforeAll(() => {
  class FakeImage {
    onload: (() => void) | null = null;
    onerror: (() => void) | null = null;
    naturalWidth = 800;
    naturalHeight = 600;
    set src(_v: string) {
      // simulate async load
      setTimeout(() => this.onload?.(), 0);
    }
  }
  // @ts-expect-error — overriding global for the test only
  global.Image = FakeImage;
});

describe("SuggestForm — PHOTO_UPLOAD branch", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("rejects unsupported file types client-side", async () => {
    render(<SuggestForm moeCode="ABC1234" onClose={jest.fn()} />);
    fireEvent.click(screen.getByLabelText(/Photo Upload/i));

    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    const badFile = new File(["dummy"], "doc.pdf", { type: "application/pdf" });
    Object.defineProperty(fileInput, "files", { value: [badFile], configurable: true });
    fireEvent.change(fileInput);

    expect(
      await screen.findByText(/Only JPEG, PNG, or WebP/i),
    ).toBeInTheDocument();
  });

  it("rejects oversize files client-side", async () => {
    render(<SuggestForm moeCode="ABC1234" onClose={jest.fn()} />);
    fireEvent.click(screen.getByLabelText(/Photo Upload/i));

    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    // Build a 6 MB JPEG-typed file (size only — content irrelevant for the size gate).
    const bigData = new Uint8Array(6 * 1024 * 1024);
    const big = new File([bigData], "huge.jpg", { type: "image/jpeg" });
    Object.defineProperty(fileInput, "files", { value: [big], configurable: true });
    fireEvent.change(fileInput);

    expect(await screen.findByText(/maximum 5 MB/i)).toBeInTheDocument();
  });

  it("surfaces backend duplicate error code as a friendly message", async () => {
    uploadMock.mockRejectedValueOnce(
      new PhotoUploadError("duplicate", 409, "dup"),
    );
    render(<SuggestForm moeCode="ABC1234" onClose={jest.fn()} />);
    fireEvent.click(screen.getByLabelText(/Photo Upload/i));

    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    const okFile = new File([new Uint8Array(1024)], "ok.jpg", { type: "image/jpeg" });
    Object.defineProperty(fileInput, "files", { value: [okFile], configurable: true });
    fireEvent.change(fileInput);

    // Wait for the preview <img> to render — confirms the file made it into state.
    await waitFor(() =>
      expect(screen.getByAltText("Preview")).toBeInTheDocument(),
    );

    // jsdom enforces native <input required> validity on form submit, so
    // clicking the submit button is blocked even though React state holds
    // the file. Submit the form directly to bypass the native validity check.
    fireEvent.submit(screen.getByRole("button", { name: /Submit/i }).closest("form")!);

    await waitFor(() => {
      expect(uploadMock).toHaveBeenCalledTimes(1);
    });
    await waitFor(() => {
      expect(
        screen.getByText(/already uploaded this photo/i),
      ).toBeInTheDocument();
    });
  });
});
