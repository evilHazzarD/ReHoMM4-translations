// The language button and note as pictures for the Linux and Switch apps (ReHoMM4 menu_button_linux.cpp
// draws them into the frame): the iOS button's look, at the game's frame
// resolution. Writes <out>/{lang,note}_<code>.argb (width, height, ARGB) for every language
// of <languages.tsv> ("code<TAB>name<TAB>restart note" per line).
//   swift tools/render_ui.swift <out dir> <languages.tsv>   (release.sh; ReHoMM4 has the same file, platforms/linux/render_ui.swift)
import AppKit

let out = CommandLine.arguments[1]
try? FileManager.default.createDirectory(atPath: out, withIntermediateDirectories: true)
let cream = NSColor(red: 0.98, green: 0.92, blue: 0.78, alpha: 1)
let gold = NSColor(red: 0.84, green: 0.67, blue: 0.34, alpha: 1)
let brown = NSColor(red: 0.10, green: 0.07, blue: 0.03, alpha: 0.92)

func render(_ name: String, _ text: String, size: CGFloat, maxWidth: CGFloat) {
  let para = NSMutableParagraphStyle(); para.alignment = .center
  let attrs: [NSAttributedString.Key: Any] = [.font: NSFont.boldSystemFont(ofSize: size),
                                             .foregroundColor: cream, .paragraphStyle: para]
  let s = NSAttributedString(string: text, attributes: attrs)
  let tb = s.boundingRect(with: NSSize(width: maxWidth, height: 1000),
                          options: [.usesLineFragmentOrigin, .usesFontLeading])
  let w = Int(ceil(tb.width)) + 28, h = Int(ceil(tb.height)) + 14
  let rep = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: w, pixelsHigh: h, bitsPerSample: 8,
                             samplesPerPixel: 4, hasAlpha: true, isPlanar: false,
                             colorSpaceName: .deviceRGB, bytesPerRow: w * 4, bitsPerPixel: 32)!
  NSGraphicsContext.saveGraphicsState()
  NSGraphicsContext.current = NSGraphicsContext(bitmapImageRep: rep)
  let r = NSRect(x: 1, y: 1, width: w - 2, height: h - 2)
  let path = NSBezierPath(roundedRect: r, xRadius: 9, yRadius: 9)
  brown.setFill(); path.fill()
  gold.setStroke(); path.lineWidth = 1.5; path.stroke()
  s.draw(with: NSRect(x: 14, y: 7, width: CGFloat(w - 28), height: tb.height),
         options: [.usesLineFragmentOrigin, .usesFontLeading])
  NSGraphicsContext.restoreGraphicsState()
  var data = Data()
  var dims = [UInt32(w).littleEndian, UInt32(h).littleEndian]
  data.append(Data(bytes: &dims, count: 8))
  for y in 0..<h {
    for x in 0..<w {
      var p = [Int](repeating: 0, count: 4)
      rep.getPixel(&p, atX: x, y: y)
      // Premultiplied in the rep: the colour as is over a dark frame; alpha cut at 0x80 when drawn.
      var v = UInt32(p[3]) << 24 | UInt32(p[0]) << 16 | UInt32(p[1]) << 8 | UInt32(p[2])
      v = v.littleEndian
      data.append(Data(bytes: &v, count: 4))
    }
  }
  try! data.write(to: URL(fileURLWithPath: "\(out)/\(name).argb"))
}

let tsv = CommandLine.arguments.count > 2 ? (try? String(contentsOfFile: CommandLine.arguments[2], encoding: .utf8)) : nil
for line in (tsv ?? "en\tEnglish\tRestart the game to apply the new language.").split(separator: "\n") {
  let f = line.split(separator: "\t", omittingEmptySubsequences: false).map(String.init)
  guard f.count >= 3 else { continue }
  render("lang_\(f[0])", "🌐 \(f[1])", size: 12, maxWidth: 400)
  render("note_\(f[0])", "\(f[1])\n\(f[2])", size: 15, maxWidth: 300)
}
