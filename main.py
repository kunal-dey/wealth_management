
from kiteconnect.exceptions import InputException
from quart import Quart, request, Blueprint
from quart_cors import cors

from constants.global_contexts import set_access_token, kite_context
from routes.stock_input import stocks_input
from services.background_process import background_task


app = Quart(__name__)
app.config['PROPAGATE_EXCEPTIONS'] = True
app = cors(app, allow_origin='*')


@app.get("/set")
async def set_token():
    """
    This route is set the access token for the kite context app to work
    :return:
    """
    set_access_token(request.args["access_token"])
    return {"message": "Token has been set"}


@app.get("/start")
async def start_process():
    """
    This route is used to start the background process
    :return:
    """
    try:
        kite_context.holdings()  # this is used to check whether there is a login error or not
        app.add_background_task(background_task)
        return {"message": "Background process has been started"}
    except InputException:
        return {"message": "Kindly login first"}


@app.route("/stop")
async def stop_background_tasks():
    """
        On being deployed if we need to manually stop the background task then
        this route is used
    """
    for task in app.background_tasks:
        task.cancel()
    return {"message": "All task cancelled"}


resource_list: list[Blueprint] = [stocks_input]

for resource in resource_list:
    app.register_blueprint(blueprint=resource)

if __name__ == "__main__":
    app.run(port=8080)
