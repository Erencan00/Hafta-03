Kullanılan kart: STM32L476RG

VSCode + CMake kullanılarak yapıldı.

SEGGER SystemView ölçümleri önce debug modda proje bir süre koşturuldu ve debug'dan çıkılarak ctrl+shift+P ile 'Task: Run Task -> SystemView Baslat' yapılıp SystemView da Start Recording ile kodun koşması incelendi. Telemetri task txQ ya veri basıyor ve UartTxTask txQ da ki verileri tüketiyor. 3 üretime 1 tüketim olarak ayarlandığı için queue doluyor (queue 20 veri tutabiliyor.). Buttona basılınca Button ISR ButtonTask'ı çalıştırıyor. Button task full dolu olan txQ sıfırlanıyor ve queue tekrar dolmaya başlıyor.