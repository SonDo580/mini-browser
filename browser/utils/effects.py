import skia


def parse_blend_mode(blend_mode: str | None) -> skia.BlendMode:
    """Convert blend mode string to Skia blend mode"""
    # CSS mix-blend-mode
    if blend_mode == "multiply":
        # color_final = color_src * color_dest
        # Effects:
        # . a (possibly) darker color (color values are in range 0.0 -> 1.0)
        # . blending with black produces black;
        #   blending with white does nothing.
        return skia.BlendMode.kMultiply

    if blend_mode == "difference":
        # color_final = |color_src - color_dest|
        # Effects:
        # - subtract darker color from lighter color
        # - blending with white inverts the destination;
        #   blending with black does nothing.
        return skia.BlendMode.kDifference

    if blend_mode == "destination-in":
        # alpha_final = alpha_dest * alpha_src
        # color_final = color_dest * alpha_src
        # Effects (if alpha_src > 0):
        # - keep only destination pixels that overlap with the source.
        # - effectively turns the incoming source shape into a clipping mask.
        # - source color is ignored.
        return skia.BlendMode.kDstIn

    # color_final = color_src + color_dest * (1 - alpha_src)
    return skia.BlendMode.kSrcOver  # standard
