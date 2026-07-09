import { PlaceholderTile } from "./PlaceholderTile";
import { type ImageBucket, useImageManifest } from "../lib/images";

interface ImageTileProps {
  name: string;
  bucket: ImageBucket;
  manifestKey: string;
  className?: string;
  textClassName?: string;
  /** Show the small "Representative image" tag when the resolved photo is
   * illustrative stock, not a real photo of this specific place. Off by
   * default for compact tiles (e.g. the 40px society thumbnail) where the
   * tag wouldn't fit; turn on for card-sized tiles. */
  showIllustrativeTag?: boolean;
}

/**
 * Exact-match lookup against image-manifest.json; no match falls back to
 * PlaceholderTile unchanged (same component, same props) - a manifest entry
 * only ever ADDS a real photo, it never removes the honest default.
 */
export function ImageTile({
  name,
  bucket,
  manifestKey,
  className = "",
  textClassName,
  showIllustrativeTag = false,
}: ImageTileProps) {
  const manifest = useImageManifest();
  const src = manifest[bucket][manifestKey];
  const illustrative = manifest.meta[bucket][manifestKey]?.illustrative === true;

  if (!src) return <PlaceholderTile name={name} className={className} textClassName={textClassName} />;

  return (
    <div className={`relative overflow-hidden ${className}`}>
      <img
        src={src}
        alt={name}
        className="h-full w-full object-cover transition-transform duration-500 ease-out group-hover:scale-105"
      />
      {showIllustrativeTag && illustrative && (
        <span
          className="absolute bottom-2 right-2 rounded-full bg-void/70 px-2 py-0.5 text-[10px] font-medium text-text-lo backdrop-blur-sm"
          title="Licensed stock, not an actual photo of this specific place"
        >
          Representative image
        </span>
      )}
    </div>
  );
}
