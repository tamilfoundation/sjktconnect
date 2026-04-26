"use client";

import Lightbox from "yet-another-react-lightbox";
import "yet-another-react-lightbox/styles.css";
import { Captions } from "yet-another-react-lightbox/plugins";
import "yet-another-react-lightbox/plugins/captions.css";

import { SchoolImageData } from "@/lib/types";

const SOURCE_LABELS: Record<string, string> = {
  SATELLITE: "Google Maps satellite",
  PLACES: "Google Places",
  STREET_VIEW: "Google Street View",
  MANUAL: "Uploaded by admin",
  COMMUNITY: "Community upload",
};

interface PhotoLightboxProps {
  open: boolean;
  index: number;
  onClose: () => void;
  images: SchoolImageData[];
  schoolName: string;
}

/**
 * Full-screen photo viewer for the school gallery (Sprint 15).
 *
 * Slides include the user-written caption (if any) plus a small attribution
 * line built from source + Google attribution string, so viewers always know
 * where a photo came from.
 */
export default function PhotoLightbox({
  open,
  index,
  onClose,
  images,
  schoolName,
}: PhotoLightboxProps) {
  const slides = images.map((img) => {
    const sourceLabel = SOURCE_LABELS[img.source] || img.source;
    const descriptionParts = [
      img.caption,
      img.attribution ? `${sourceLabel} — ${img.attribution}` : sourceLabel,
    ].filter(Boolean);
    // Caption goes in `description` only; the Captions plugin renders it
    // as a single footer block. Setting `title` would duplicate the caption
    // as a top-left header on top of the same footer.
    return {
      src: img.image_url,
      alt: img.caption || schoolName,
      description: descriptionParts.join(" · "),
    };
  });

  return (
    <Lightbox
      open={open}
      close={onClose}
      index={index}
      slides={slides}
      plugins={[Captions]}
      captions={{
        descriptionTextAlign: "center",
        descriptionMaxLines: 3,
      }}
      animation={{ fade: 250, swipe: 250 }}
      controller={{ closeOnBackdropClick: true }}
    />
  );
}
