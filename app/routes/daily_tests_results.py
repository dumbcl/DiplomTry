from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session
from app import models, auth, database
from app.outside_logic.fs_description import generate_fs_description
from app.outside_logic.fs_score import evaluate_shtange, evaluate_rufie, evaluate_strup, evaluate_gench, evaluate_pulse, evaluate_personal_report, calculate_fs_category, \
    evaluate_text_audition, evaluate_reactions
from app.schemas import DailyTestResult, ShtangeTestResult, ReactionsTestResult, TextAuditionTestResult, \
    GenchTestResult, StrupTestResult, RufieTestResult, PulseMeasurementResult, PersonalReportTestResult

router = APIRouter()

def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/daily-test-results", response_model=List[DailyTestResult])
def get_daily_test_results(db: Session = Depends(get_db), user: models.User = Depends(auth.get_current_user)):
    # Получаем все уникальные даты, когда пользователь проходил тесты
    unique_test_dates = db.query(models.ShtangeTestResult.test_date).filter_by(user_id=user.id).distinct().all()
    unique_test_dates += db.query(models.PersonalReportTestResult.test_date).filter_by(user_id=user.id).distinct().all()
    #unique_test_dates += db.query(models.PulseMeasurement.measured_at).filter_by(user_id=user.id).distinct().all()
    unique_test_dates += db.query(models.RufieTestResult.test_date).filter_by(user_id=user.id).distinct().all()
    unique_test_dates += db.query(models.StrupTestResult.test_date).filter_by(user_id=user.id).distinct().all()
    unique_test_dates += db.query(models.GenchTestResult.test_date).filter_by(user_id=user.id).distinct().all()
    unique_test_dates += db.query(models.ReactionsTestResult.test_date).filter_by(user_id=user.id).distinct().all()
    unique_test_dates += db.query(models.TextAuditionResults.test_date).filter_by(user_id=user.id).distinct().all()

    # Убираем дублированные даты
    unique_test_dates = list(set([date[0] for date in unique_test_dates]))

    daily_results = []

    for test_date in sorted(unique_test_dates, reverse=True):
        # Запрашиваем результаты из разных таблиц для конкретной даты
        shtange_results = db.query(models.ShtangeTestResult).filter_by(user_id=user.id, test_date=test_date).all()
        shtange_result = shtange_results[0].result_estimation if shtange_results else None
        shtange_result_indicator = shtange_results[0].reaction_indicator if shtange_results else None
        shtange_test_result_indicator_average = db.query(func.avg(models.ShtangeTestResult.reaction_indicator)).filter_by(user_id=user.id).scalar()

        # PersonalReportTestResult для этого дня
        personal_report_result = db.query(models.PersonalReportTestResult).filter_by(user_id=user.id, test_date=test_date).first()
        personal_report = personal_report_result.days_comparison if personal_report_result else None
        personal_report_indicator = personal_report_result.performance_measure if personal_report_result else None
        personal_report_all = db.query(models.PersonalReportTestResult).filter_by(user_id=user.id).all()
        personal_report_indicator_average = sum([pm.performance_measure for pm in personal_report_all]) / len(personal_report_all) if personal_report_all else None

        # PulseMeasurement для этого дня
        pulse_measurements = db.query(models.PulseMeasurement).filter_by(user_id=user.id, created_at=test_date).all()
        pulseAverage = sum([pm.value for pm in pulse_measurements]) / len(pulse_measurements) if pulse_measurements else None
        pulseMax = max([pm.value for pm in pulse_measurements], default=None)
        pulseMin = min([pm.value for pm in pulse_measurements], default=None)
        pulse_alltime_measurements = db.query(models.PulseMeasurement).filter_by(user_id=user.id).all()
        pulse_alltime_average = sum([pm.value for pm in pulse_alltime_measurements]) / len(pulse_alltime_measurements) if pulse_alltime_measurements else None

        # RufieTestResult для этого дня
        rufie_results = db.query(models.RufieTestResult).filter_by(user_id=user.id, test_date=test_date).all()
        rufie_result = rufie_results[0].result_estimation if rufie_results else None
        rufie_result_indicator = rufie_results[0].rufie_index if rufie_results else None
        rufie_test_result_indicator_average = db.query(func.avg(models.RufieTestResult.rufie_index)).filter_by(user_id=user.id).scalar()

        # StrupTestResult для этого дня
        strup_results = db.query(models.StrupTestResult).filter_by(user_id=user.id, test_date=test_date).all()
        strup_result_estimation = strup_results[0].result_estimation if strup_results else None
        strup_result = strup_results[0].result if strup_results else None
        strup_test_result_average = db.query(func.avg(models.StrupTestResult.result)).filter_by(user_id=user.id).scalar()

        # GenchTestResult для этого дня
        gench_results = db.query(models.GenchTestResult).filter_by(user_id=user.id, test_date=test_date).all()
        gench_result_estimation = gench_results[0].result_estimation if gench_results else None
        gench_result_indicator = gench_results[0].reaction_indicator if gench_results else None
       #check
        gench_test_result_indicator_average = db.query(func.avg(models.GenchTestResult.reaction_indicator)).filter_by(user_id=user.id).scalar()

        # ReactionsTestResult для этого дня
        reactions_results = db.query(models.ReactionsTestResult).filter_by(user_id=user.id, test_date=test_date).all()
        reactions_visual_errors = reactions_results[0].visual_errors if reactions_results else None
        reactions_audio_errors = reactions_results[0].audio_errors if reactions_results else None
        reactions_visual_errors_average = db.query(func.avg(models.ReactionsTestResult.visual_errors)).filter_by(user_id=user.id).scalar()
        reactions_audio_errors_average = db.query(func.avg(models.ReactionsTestResult.audio_errors)).filter_by(user_id=user.id).scalar()

        # TextAuditionResults для этого дня
        text_audition_results = db.query(models.TextAuditionResults).filter_by(user_id=user.id, test_date=test_date).all()
        pauses_count_read = text_audition_results[0].pauses_count_read if text_audition_results else None
        pauses_count_repeat = text_audition_results[0].pauses_count_repeat if text_audition_results else None
        pauses_count_read_average = db.query(func.avg(models.TextAuditionResults.pauses_count_read)).filter_by(user_id=user.id).scalar()
        pauses_count_repeat_average = db.query(func.avg(models.TextAuditionResults.pauses_count_repeat)).filter_by(user_id=user.id).scalar()
        average_volume_read = text_audition_results[0].average_volume_read if text_audition_results else None
        average_volume_repeat = text_audition_results[0].average_volume_repeat if text_audition_results else None
        average_volume_read_average = db.query(func.avg(models.TextAuditionResults.average_volume_read)).filter_by(user_id=user.id).scalar()
        average_volume_repeat_average = db.query(func.avg(models.TextAuditionResults.average_volume_repeat)).filter_by(user_id=user.id).scalar()

        fs_category = calculate_fs_category(
            shtange_result_indicator=shtange_result_indicator,
            shtange_test_result_indicator_average=shtange_test_result_indicator_average,
            personal_report=personal_report_indicator,
            personal_report_average=personal_report_indicator_average,
            pulseAverage=pulseAverage,
            pulseAverageAllDays=pulse_alltime_average,
            rufie_result_indicator=rufie_result_indicator,
            strup_result=strup_result,
            strup_test_result_average=strup_test_result_average,
            gench_result_indicator=gench_result_indicator,
            gench_test_result_indicator_average=gench_test_result_indicator_average,
            reactions_visual_errors=reactions_visual_errors,
            reactions_audio_errors=reactions_audio_errors,
            reactions_visual_errors_average=reactions_visual_errors_average,
            reactions_audio_errors_average=reactions_audio_errors_average,
            pauses_count_read=pauses_count_read,
            pauses_count_repeat=pauses_count_repeat,
            pauses_count_read_average=pauses_count_read_average,
            pauses_count_repeat_average=pauses_count_repeat_average,
            average_volume_read=average_volume_read,
            average_volume_repeat=average_volume_repeat,
            average_volume_read_average=average_volume_read_average,
            average_volume_repeat_average=average_volume_repeat_average
        )

        # Собираем результаты в одном объекте
        result = DailyTestResult(
            date=str(test_date),
            shtange_test_result = evaluate_shtange(
                shtange_result = shtange_result,
                shtange_result_indicator = shtange_result_indicator,
                shtange_average = shtange_test_result_indicator_average,
            ),
            personal_report = evaluate_personal_report(
                report_text=personal_report,
                report_current=personal_report_indicator,
                report_average=personal_report_indicator_average,
            ),
            pulse_measurement = evaluate_pulse(
                pulse_avg = pulseAverage,
                pulse_max = pulseMax,
                pulse_min = pulseMin,
                pulse_alltime_avg=pulse_alltime_average
            ),
            rufie_test_result = evaluate_rufie(
                rufie_result = rufie_result,
                rufie_indicator = rufie_result_indicator,
                rufie_avg= rufie_test_result_indicator_average,
            ),
            strup_test_result = evaluate_strup(
                strup_result = strup_result,
                strup_avg = strup_test_result_average,
                strup_result_estimation=strup_result_estimation,
            ),
            gench_test_result = evaluate_gench(
                gench_indicator = gench_result_indicator,
                gench_result_estimation=gench_result_estimation,
                gench_avg=gench_test_result_indicator_average,
            ),
            reactions_test_result = evaluate_reactions(
                visual = reactions_visual_errors,
                audio = reactions_audio_errors,
                visual_avg = reactions_visual_errors_average,
                audio_avg=reactions_audio_errors_average,
            ),
            text_audition_test_result = evaluate_text_audition(
                pauses_read=pauses_count_read,
                pauses_read_avg=pauses_count_read_average,
                pauses_repeat_avg=pauses_count_repeat_average,
                pauses_repeat=pauses_count_repeat,
                vol_read=average_volume_read,
                vol_repeat=average_volume_repeat,
                vol_read_avg=average_volume_read_average,
                vol_repeat_avg=average_volume_repeat_average,
            ),
            day_description=generate_fs_description(
                shtange_result_indicator = shtange_result_indicator,
                shtange_test_result_indicator_average = shtange_test_result_indicator_average,
                personal_report = personal_report_indicator,
                personal_report_average = personal_report_indicator_average,
                pulseAverage = pulseAverage,
                pulseAverageAllDays = pulse_alltime_average,
                rufie_result_indicator = rufie_result_indicator,
                strup_result = strup_result,
                strup_test_result_average = strup_test_result_average,
                gench_result_indicator = gench_result_indicator,
                gench_test_result_indicator_average = gench_test_result_indicator_average,
                reactions_visual_errors = reactions_visual_errors,
                reactions_audio_errors = reactions_audio_errors,
                reactions_visual_errors_average = reactions_visual_errors_average,
                reactions_audio_errors_average = reactions_audio_errors_average,
                pauses_count_read = pauses_count_read,
                pauses_count_repeat = pauses_count_repeat,
                pauses_count_read_average = pauses_count_read_average,
                pauses_count_repeat_average = pauses_count_repeat_average,
                average_volume_read = average_volume_read,
                average_volume_repeat = average_volume_repeat,
                average_volume_read_average = average_volume_read_average,
                average_volume_repeat_average = average_volume_repeat_average,
                fs_category = fs_category,
            ),
            day_type=fs_category,
        )

        daily_results.append(result)

    return daily_results
