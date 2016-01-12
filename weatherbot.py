#!/usr/bin/python
# -*- encoding: utf-8 -*-
#
# Copyright (c) 2014-2015 by deflax <daniel@deflax.net>
#
#       Weechat WeatherBot using WUnderground API
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import weechat
import ast

SCRIPT_NAME = "weatherbot"
VERSION = "0.6"

helptext = """
Get your own API key from http://www.wunderground.com/weather/api/
and act as a weatherbot :)

Hugs to all friends from #clanchill @ quakenet \o/
"""

default_options = {"enabled": "off",
                   "units": "metric",
                   "trigger": "!weather",
                   "apikey": "0000000000000"}

def weebuffer(reaction_buf):
    rtnbuf = "{},{}".format(kserver, kchannel)
    buffer = weechat.info_get("irc_buffer", rtnbuf)
    weechat.command(buffer, "/msg {} {}".format(kchannel, reaction_buf))

def wu_autoc(data, command, return_code, out, err):
    global jname
    if return_code == weechat.WEECHAT_HOOK_PROCESS_ERROR:
        weechat.prnt("", "Error with command `%s'" % command)
        return weechat.WEECHAT_RC_OK
    if return_code > 0:
        weechat.prnt("", "return_code = %d" % return_code)
    if err != "":
        weechat.prnt("", "stderr: %s" % err)
    if out != "":
        i = ast.literal_eval(out)
        try:
            loc = next((l for l in i["RESULTS"] if l["type"] == "city"), None)
            if loc is None:
                weebuffer("Unable to locate query.")
                return weechat.WEECHAT_RC_OK
        except:
            weebuffer("Invalid query. Try again.")
            return weechat.WEECHAT_RC_OK

        jname = loc["name"]
        cond_url = "url:http://api.wunderground.com/api/{}/conditions{}.json".format(options["apikey"], loc["l"])
        weechat.hook_process(cond_url, 30 * 1000, "wu_cond", "")
    return weechat.WEECHAT_RC_OK

def wu_cond(data, command, return_code, out, err):
    if return_code == weechat.WEECHAT_HOOK_PROCESS_ERROR:
        weechat.prnt("", "Error with command '%s'" % command)
        return weechat.WEECHAT_RC_OK
    if return_code > 0:
        weechat.prnt("", "return_code = %d" % return_code)
    if err != "":
        weechat.prnt("", "stderr: %s" % err)
    if out != "":
        j = ast.literal_eval(out)
        try:
            error_type = j["response"]["error"]["type"]
            if error_type == "invalidquery":
                weebuffer("Error. Try again.")
                return weechat.WEECHAT_RC_OK
            elif error_type == "keynotfound":
                weechat.prnt("", "Invalid API key.")
                return weechat.WEECHAT_RC_OK
        except KeyError:
            pass

        co = j["current_observation"]
        reaction = "[{}] {}. Temp is ".format(jname, co["weather"])

        if options["units"] == "metric":
            temp_unit = "C"
            wind_unit = "kph"
        else:
            temp_unit = "F"
            wind_unit = "mph"

        temp = co["temp_{}".format(temp_unit.lower())]
        like = co["feelslike_{}".format(temp_unit.lower())]
        if abs(int(float(temp)) - int(float(like))) > 2:
            reaction += "{0}°{1} but feels like {2}°{1}.".format(temp, temp_unit, like)
        else:
            reaction += "{}°{}.".format(temp, temp_unit)

        wind_speed = co["wind_{}".format(wind_unit)]
        if wind_speed > 0:
            reaction += " {} wind: {} {}.".format(co["wind_dir"], wind_speed, wind_unit)

        humid = co["relative_humidity"]
        if int(humid[:-1]) > 50:
            reaction += " Humidity: {}.".format(co["relative_humidity"])

        weebuffer(reaction)
    return weechat.WEECHAT_RC_OK

def triggerwatch(data, server, args):
    global kserver, kchannel
    if options["enabled"] == "on":
        try:
            null, srvmsg = args.split(" PRIVMSG ", 1)
            kchannel, query = srvmsg.split(" :{} ".format(options["trigger"]), 1)
        except ValueError:
            return weechat.WEECHAT_RC_OK
        kserver = str(server.split(",", 1)[0])
        query = query.replace(" ", "%20")
        autoc_url = "url:http://autocomplete.wunderground.com/aq?query={}&format=JSON".format(query)
        weechat.hook_process(autoc_url, 30 * 1000, "wu_autoc", "")

    return weechat.WEECHAT_RC_OK

weechat.register("weatherbot", "deflax", VERSION, "GPL3", "WeatherBot using the WeatherUnderground API", "", "")
weechat.hook_signal("*,irc_in_privmsg", "triggerwatch", "data")

def config_cb(data, option, value):
    """Callback called when a script option is changed."""
    opt = option.split(".")[-1]
    options[opt] = value
    return weechat.WEECHAT_RC_OK

def get_option(option):
    """Returns value of weechat option."""
    return weechat.config_string(weechat.config_get("{}.{}".format(plugin_config, option)))

plugin_config = "plugins.var.python.{}".format(SCRIPT_NAME)
weechat.hook_config("{}.*".format(plugin_config), "config_cb", "")
for option, default_value in default_options.items():
    if not weechat.config_is_set_plugin(option):
        weechat.config_set_plugin(option, default_value)

options = {"enabled": get_option("enabled"), "units": get_option("units"), "trigger": get_option("trigger"),
           "apikey": get_option("apikey")}

if options["apikey"] == "0000000000000":
    weechat.prnt("", "Your API key is not set. Please sign up at www.wunderground.com/weather/api "
                     "and set plugins.var.python.weatherbot.* options. Thanks.")
