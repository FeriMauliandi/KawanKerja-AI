/**
 * KawanKerja AI - Modul Kalkulator Hak Ketenagakerjaan
 * Berdasarkan formula resmi Peraturan Pemerintah (PP) No. 35 Tahun 2021
 */

const LegalCalculator = {
    formatRupiah(number) {
        return new Intl.NumberFormat('id-ID', {
            style: 'currency',
            currency: 'IDR',
            maximumFractionDigits: 0
        }).format(number);
    },

    /**
     * Hitung Uang Kompensasi PKWT (Pasal 15, 16 PP No. 35/2021)
     * Rumus: (Masa Kerja dalam Bulan / 12) * 1 Bulan Upah
     */
    calculatePKWTCompensation(months, monthlyWage) {
        if (months < 1) {
            return {
                amount: 0,
                eligible: false,
                reason: "Masa kerja kurang dari 1 bulan tidak berhak mendapatkan uang kompensasi (Pasal 15 ayat 2).",
                formula: "Masa kerja < 1 bulan"
            };
        }

        const compensation = (months / 12) * monthlyWage;
        return {
            amount: Math.round(compensation),
            eligible: true,
            months: months,
            wage: monthlyWage,
            formula: `(${months} / 12) × ${this.formatRupiah(monthlyWage)}`,
            pasalRef: "Pasal 15 ayat (1) huruf a, b, dan c PP No. 35 Tahun 2021",
            notes: "Kompensasi diberikan pada saat berakhirnya jangka waktu PKWT maupun perpanjangannya."
        };
    },

    /**
     * Hitung Upah Kerja Lembur (Pasal 31 - 32 PP No. 35/2021)
     * Upah per jam = 1 / 173 * Upah sebulan
     */
    calculateOvertimeWage(monthlyWage, overtimeHours, dayType = 'workday') {
        const hourlyRate = monthlyWage / 173;
        let totalOvertimePay = 0;
        let breakdown = [];

        if (dayType === 'workday') {
            // Hari kerja biasa
            // Jam ke-1: 1.5x upah sejam, jam ke-2 dst: 2x upah sejam
            if (overtimeHours <= 1) {
                const pay = overtimeHours * 1.5 * hourlyRate;
                totalOvertimePay += pay;
                breakdown.push(`Jam ke-1: ${overtimeHours} jam × 1.5 × ${this.formatRupiah(hourlyRate)} = ${this.formatRupiah(pay)}`);
            } else {
                const pay1 = 1 * 1.5 * hourlyRate;
                const hoursNext = overtimeHours - 1;
                const payNext = hoursNext * 2.0 * hourlyRate;
                totalOvertimePay = pay1 + payNext;
                breakdown.push(`Jam ke-1: 1 jam × 1.5 × ${this.formatRupiah(hourlyRate)} = ${this.formatRupiah(pay1)}`);
                breakdown.push(`Jam ke-2 s.d ${overtimeHours}: ${hoursNext} jam × 2.0 × ${this.formatRupiah(hourlyRate)} = ${this.formatRupiah(payNext)}`);
            }
        } else {
            // Hari Libur Resmi / Istirahat Mingguan (skema 5 hari kerja / 40 jam seminggu)
            let remaining = overtimeHours;
            if (remaining > 0) {
                const h1 = Math.min(remaining, 8);
                const pay1 = h1 * 2 * hourlyRate;
                totalOvertimePay += pay1;
                breakdown.push(`8 Jam Pertama: ${h1} jam × 2 × ${this.formatRupiah(hourlyRate)} = ${this.formatRupiah(pay1)}`);
                remaining -= h1;
            }
            if (remaining > 0) {
                const h2 = Math.min(remaining, 1);
                const pay2 = h2 * 3 * hourlyRate;
                totalOvertimePay += pay2;
                breakdown.push(`Jam ke-9: ${h2} jam × 3 × ${this.formatRupiah(hourlyRate)} = ${this.formatRupiah(pay2)}`);
                remaining -= h2;
            }
            if (remaining > 0) {
                const pay3 = remaining * 4 * hourlyRate;
                totalOvertimePay += pay3;
                breakdown.push(`Jam ke-10 s.d 12: ${remaining} jam × 4 × ${this.formatRupiah(hourlyRate)} = ${this.formatRupiah(pay3)}`);
            }
        }

        return {
            hourlyRate: Math.round(hourlyRate),
            totalPay: Math.round(totalOvertimePay),
            breakdown: breakdown,
            pasalRef: "Pasal 31 & 32 PP No. 35 Tahun 2021"
        };
    },

    /**
     * Hitung Estimasi Uang Pesangon & UPMK PHK (Pasal 40 PP No. 35/2021)
     */
    calculateSeverance(yearsOfService, monthlyWage, multiplier = 1.0) {
        // Skala Pesangon (Pasal 40 ayat 2)
        let pesangonMonths = 0;
        if (yearsOfService < 1) pesangonMonths = 1;
        else if (yearsOfService < 2) pesangonMonths = 2;
        else if (yearsOfService < 3) pesangonMonths = 3;
        else if (yearsOfService < 4) pesangonMonths = 4;
        else if (yearsOfService < 5) pesangonMonths = 5;
        else if (yearsOfService < 6) pesangonMonths = 6;
        else if (yearsOfService < 7) pesangonMonths = 7;
        else if (yearsOfService < 8) pesangonMonths = 8;
        else pesangonMonths = 9;

        // Skala UPMK (Pasal 40 ayat 3)
        let upmkMonths = 0;
        if (yearsOfService >= 3 && yearsOfService < 6) upmkMonths = 2;
        else if (yearsOfService >= 6 && yearsOfService < 9) upmkMonths = 3;
        else if (yearsOfService >= 9 && yearsOfService < 12) upmkMonths = 4;
        else if (yearsOfService >= 12 && yearsOfService < 15) upmkMonths = 5;
        else if (yearsOfService >= 15 && yearsOfService < 18) upmkMonths = 6;
        else if (yearsOfService >= 18 && yearsOfService < 21) upmkMonths = 7;
        else if (yearsOfService >= 21 && yearsOfService < 24) upmkMonths = 8;
        else if (yearsOfService >= 24) upmkMonths = 10;

        const basePesangon = pesangonMonths * monthlyWage;
        const totalPesangon = basePesangon * multiplier;
        const totalUPMK = upmkMonths * monthlyWage; // UPMK umumnya 1x sesuai pasal terkait
        const totalEstimate = totalPesangon + totalUPMK;

        return {
            years: yearsOfService,
            pesangonMonths: pesangonMonths,
            multiplier: multiplier,
            basePesangon: basePesangon,
            totalPesangon: Math.round(totalPesangon),
            upmkMonths: upmkMonths,
            totalUPMK: Math.round(totalUPMK),
            totalEstimate: Math.round(totalEstimate),
            pasalRef: "Pasal 40 - 59 PP No. 35 Tahun 2021"
        };
    }
};

window.LegalCalculator = LegalCalculator;
