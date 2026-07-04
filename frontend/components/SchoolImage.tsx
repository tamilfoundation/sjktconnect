"use client";

import dynamic from "next/dynamic";
import { useState } from "react";
import { useTranslations } from "next-intl";
import { SchoolImageData } from "@/lib/types";

// Lazy: lightbox is heavy and only loads when a user clicks. Also
// avoids SSR issues — the lib touches `window` at import time.
const PhotoLightbox = dynamic(() => import("./PhotoLightbox"), { ssr: false });

interface Props {
  images?: SchoolImageData[];
  schoolName: string;
  imageUrl?: string | null;
}

export default function SchoolPhotoGallery({
  images,
  schoolName,
  imageUrl,
}: Props) {
  const t = useTranslations("parliamentWatch");

  let photoList: SchoolImageData[];
  if (images && images.length > 0) {
    photoList = images;
  } else if (imageUrl) {
    photoList = [
      {
        id: 0,
        image_url: imageUrl,
        source: "PLACES" as const,
        position: 0,
        is_primary: true,
        attribution: "",
        caption: "",
      },
    ];
  } else {
    photoList = [];
  }

  const [activeIndex, setActiveIndex] = useState(0);
  const [lightboxOpen, setLightboxOpen] = useState(false);
  const [lightboxIndex, setLightboxIndex] = useState(0);

  const openLightbox = (i: number) => {
    setLightboxIndex(i);
    setLightboxOpen(true);
  };

  if (photoList.length === 0) {
    // (Sprint 22) Render the branded placeholder as a real <img> instead
    // of just "No photo" text so Google's SERP thumbnail picker has
    // something to use. Schools without uploaded images previously
    // showed up text-only in search and lost clicks to competitors.
    return (
      <div className="relative w-full h-64 sm:h-80 lg:h-[400px] rounded-xl overflow-hidden bg-indigo-900">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src="/school-placeholder.svg"
          alt={`${schoolName} — Tamil primary school (SJK(T))`}
          className="w-full h-full object-cover"
          loading="lazy"
        />
        <div className="absolute inset-0 flex items-end justify-center pb-6">
          <p className="text-indigo-100 text-xs font-medium tracking-wide">
            {t("noPhoto")}
          </p>
        </div>
      </div>
    );
  }

  const active = photoList[activeIndex];

  return (
    <>
      <div className="relative w-full h-64 sm:h-80 lg:h-[400px] rounded-xl overflow-hidden shadow-sm bg-gray-200 group">
        {/* Main image — clickable to open lightbox */}
        <button
          onClick={() => openLightbox(activeIndex)}
          className="block w-full h-full focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-500"
          aria-label={`Open ${schoolName} photo viewer`}
        >
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={active.image_url}
            alt={active.caption || schoolName}
            className="w-full h-full object-cover"
            loading="lazy"
          />
        </button>

        {/* Caption is rendered in the lightbox + image manager only — putting
            it on the hero collides with the thumbnail strip and the attribution
            tag, both of which already anchor to the bottom edge. */}

        {/* "View all N photos" overlay — top-right when there are more than 5 */}
        {photoList.length > 5 && (
          <button
            onClick={() => openLightbox(0)}
            className="absolute top-3 right-3 text-xs text-white bg-black/60 hover:bg-black/80 px-3 py-1.5 rounded-full backdrop-blur-sm font-medium transition-colors"
          >
            View all {photoList.length} photos
          </button>
        )}

        {/* Attribution (bottom-right) */}
        {active.attribution && (
          <div className="pointer-events-none absolute bottom-3 right-3 text-[10px] text-white/80 bg-black/40 px-2 py-1 rounded backdrop-blur-sm">
            {t("photoCredit")} {active.attribution.replace(/<[^>]*>/g, "")}
          </div>
        )}

        {/* Thumbnail strip overlaid at bottom-left. Shows up to 5; when
            there are 6+ photos the "View all" overlay (above) lets users
            jump into the lightbox. Before the bump to 5 (2026-06-28) a
            school with exactly 5 photos had its 5th silently dropped.
            Audit 2026-07-01: below sm (375 px) thumbs 4-5 overflowed
            the hero width. On xs viewports we cap to 3 visible; the
            "View all" overlay still lets users see the rest.  */}
        {photoList.length > 1 && (
          <div className="absolute bottom-3 left-3 flex gap-2">
            {photoList.slice(0, 5).map((img, i) => (
              <button
                key={img.id || i}
                onClick={(e) => {
                  e.stopPropagation();
                  // single-click: switch the hero; double-click handled by
                  // separate lightbox open via the hero button.
                  setActiveIndex(i);
                }}
                onDoubleClick={() => openLightbox(i)}
                className={`w-16 h-12 sm:w-20 sm:h-14 rounded-lg overflow-hidden flex-shrink-0 transition-all ${
                  i >= 3 ? "hidden sm:block" : ""
                } ${
                  i === activeIndex
                    ? "border-2 border-primary-500 opacity-100"
                    : "border border-white/50 opacity-70 hover:opacity-100"
                }`}
                title="Click to set as hero · Double-click to open viewer"
              >
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={img.image_url}
                  alt={img.caption || `${schoolName} photo ${i + 1}`}
                  className="w-full h-full object-cover"
                  loading="lazy"
                />
              </button>
            ))}
          </div>
        )}
      </div>

      {lightboxOpen && (
        <PhotoLightbox
          open={lightboxOpen}
          index={lightboxIndex}
          onClose={() => setLightboxOpen(false)}
          images={photoList}
          schoolName={schoolName}
        />
      )}
    </>
  );
}
