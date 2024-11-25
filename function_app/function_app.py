import logging

import azure.functions as func

from ptu_data_export import export_ptu_data

# Set the logging level for all azure-* libraries
logger = logging.getLogger('azure')
logger.setLevel(logging.ERROR)

app = func.FunctionApp()

@app.timer_trigger(schedule="0 */5 * * * *", arg_name="myTimer", run_on_startup=False,
              use_monitor=False) 
async def timer_trigger(myTimer: func.TimerRequest) -> None:
    logging.info('Refreshing PTU Data...')
    await export_ptu_data()
    logging.info('Data Refresh Complete!')
