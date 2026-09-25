// Прототип 2: настоящий OFX-плагин (тот путь, которым сделан Procedural CRT).
//
// ВНИМАНИЕ: этот файл нельзя собрать в текущей облачной сессии — здесь нет
// macOS, Xcode, Metal-тулчейна и самого Resolve. Это исходник, который нужно
// перенести на твой Mac и собрать там (см. README.md рядом).
//
// Что показывает прототип:
//  - три параметра (PixelSize, Glow, Scanlines) — с кастомным overlay-интерактом,
//    т.е. рисуем СВОИ виджеты (не стандартные Resolve-слайдеры) прямо в области
//    вьюера, как на сайте-референсе;
//  - простейший CPU-рендер (тонирование по X/Y), чтобы было видно, что эффект
//    реально применяется к картинке, а не только к UI.
//
// Основано на официальном OFX C++ Support library (openfx-supportext),
// который используется большинством коммерческих OFX-плагинов для Resolve/Fusion/Nuke.

#include "ofxsImageEffect.h"
#include "ofxsInteract.h"
#include "ofxsProcessing.h"

using namespace OFX;

////////////////////////////////////////////////////////////////////////////
// Свой overlay-интеракт: рисуем три "плашки"-слайдера прямо во вьюере,
// вместо того чтобы полагаться на стандартную панель параметров Resolve.
// Это и есть механизм, которым делают "плавающий кастомный UI поверх".
class CRTProtoInteract : public OverlayInteract
{
public:
    explicit CRTProtoInteract(OfxInteractHandle handle, ImageEffect* effect)
        : OverlayInteract(handle), _effect(effect) {}

    virtual bool draw(const DrawArgs& args) OVERRIDE
    {
        // Здесь в реальном плагине идёт OpenGL/иммедиат-рисование трёх
        // прямоугольников-слайдеров со своими цветами/шрифтом — то, что
        // на референс-сайте выглядит как "не-Resolve" окно.
        // Для прототипа оставляем структуру вызова без реальной отрисовки.
        (void)args;
        return true;
    }

    virtual bool penDown(const PenArgs& args) OVERRIDE
    {
        // Хит-тест по трём зонам слайдеров, драг мышью двигает параметр.
        (void)args;
        return false;
    }

private:
    ImageEffect* _effect;
};

class CRTProtoInteractDescriptor : public DefaultEffectOverlayDescriptor<CRTProtoInteractDescriptor, CRTProtoInteract> {};

////////////////////////////////////////////////////////////////////////////
// Сам эффект: три Double-параметра + CPU-процессор, который применяет их
// к изображению (упрощённо, для прототипа — просто модулирует яркость по
// синусоиде от PixelSize, имитируя "что-то происходит").
class CRTProtoProcessor : public ImageProcessor
{
public:
    explicit CRTProtoProcessor(ImageEffect& instance) : ImageProcessor(instance) {}

    void setSrcImg(Image* src) { _srcImg = src; }
    void setParams(double pixelSize, double glow, double scan)
    {
        _pixelSize = pixelSize; _glow = glow; _scan = scan;
    }

    virtual void multiThreadProcessImages(OfxRectI procWindow) OVERRIDE
    {
        for (int y = procWindow.y1; y < procWindow.y2; ++y) {
            float* dstPix = (float*)_dstImg->getPixelAddress(procWindow.x1, y);
            for (int x = procWindow.x1; x < procWindow.x2; ++x) {
                float* srcPix = _srcImg ? (float*)_srcImg->getPixelAddress(x, y) : nullptr;
                for (int c = 0; c < 4; ++c) {
                    float v = srcPix ? srcPix[c] : 0.0f;
                    // Простейшая имитация "работает": лёгкая модуляция по X с шагом pixelSize.
                    double stripe = (fmod((double)x, _pixelSize > 0 ? _pixelSize : 1.0) < _pixelSize * 0.5) ? 1.0 : (1.0 - _glow * 0.01);
                    dstPix[c] = c == 3 ? v : (float)(v * stripe);
                }
                dstPix += 4;
            }
        }
        (void)_scan;
    }

private:
    Image* _srcImg = nullptr;
    double _pixelSize = 4.0, _glow = 30.0, _scan = 50.0;
};

class CRTProtoPlugin : public ImageEffect
{
public:
    explicit CRTProtoPlugin(OfxImageEffectHandle handle) : ImageEffect(handle)
    {
        _srcClip = fetchClip(kOfxImageEffectSimpleSourceClipName);
        _dstClip = fetchClip(kOfxImageEffectOutputClipName);
        _pixelSize = fetchDoubleParam("pixelSize");
        _glow = fetchDoubleParam("glow");
        _scanlines = fetchDoubleParam("scanlines");
    }

    virtual void render(const RenderArguments& args) OVERRIDE
    {
        std::unique_ptr<Image> dst(_dstClip->fetchImage(args.time));
        std::unique_ptr<Image> src(_srcClip->fetchImage(args.time));

        CRTProtoProcessor proc(*this);
        proc.setDstImg(dst.get());
        proc.setSrcImg(src.get());

        double ps, gl, sc;
        _pixelSize->getValueAtTime(args.time, ps);
        _glow->getValueAtTime(args.time, gl);
        _scanlines->getValueAtTime(args.time, sc);
        proc.setParams(ps, gl, sc);

        proc.setRenderWindow(args.renderWindow);
        proc.process();
    }

private:
    Clip* _srcClip;
    Clip* _dstClip;
    DoubleParam* _pixelSize;
    DoubleParam* _glow;
    DoubleParam* _scanlines;
};

////////////////////////////////////////////////////////////////////////////
class CRTProtoPluginFactory : public PluginFactoryHelper<CRTProtoPluginFactory>
{
public:
    CRTProtoPluginFactory() : PluginFactoryHelper<CRTProtoPluginFactory>(
        "com.claude.CRTProtoPlugin", 1, 0) {}

    virtual void describe(ImageEffectDescriptor& desc) OVERRIDE
    {
        desc.setLabels("CRT Proto (OFX)", "CRT Proto", "CRT Proto");
        desc.setPluginGrouping("Claude");
        desc.addSupportedContext(eContextFilter);
        desc.addSupportedBitDepth(eBitDepthFloat);
        desc.setSupportsTiles(false);
        desc.setOverlayInteractDescriptor(new CRTProtoInteractDescriptor());
    }

    virtual void describeInContext(ImageEffectDescriptor& desc, ContextEnum /*context*/) OVERRIDE
    {
        ClipDescriptor* srcClip = desc.defineClip(kOfxImageEffectSimpleSourceClipName);
        srcClip->addSupportedComponent(ePixelComponentRGBA);

        ClipDescriptor* dstClip = desc.defineClip(kOfxImageEffectOutputClipName);
        dstClip->addSupportedComponent(ePixelComponentRGBA);

        DoubleParamDescriptor* pixelSize = desc.defineDoubleParam("pixelSize");
        pixelSize->setLabels("Размер пикселя", "Pixel Size", "Pixel Size");
        pixelSize->setRange(1.0, 40.0);
        pixelSize->setDisplayRange(1.0, 20.0);
        pixelSize->setDefault(4.0);

        DoubleParamDescriptor* glow = desc.defineDoubleParam("glow");
        glow->setLabels("Свечение", "Glow", "Glow");
        glow->setRange(0.0, 100.0);
        glow->setDefault(30.0);

        DoubleParamDescriptor* scan = desc.defineDoubleParam("scanlines");
        scan->setLabels("Развёртка", "Scanlines", "Scanlines");
        scan->setRange(0.0, 100.0);
        scan->setDefault(50.0);
    }

    virtual ImageEffect* createInstance(OfxImageEffectHandle handle, ContextEnum /*context*/) OVERRIDE
    {
        return new CRTProtoPlugin(handle);
    }
};

void getPluginIDs(PluginFactoryArray& ids)
{
    static CRTProtoPluginFactory p;
    ids.push_back(&p);
}
